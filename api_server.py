"""Backend API for Chrome Extension — indexes pages and answers queries via FAISS."""
from __future__ import annotations

import json
import uuid
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory import memory
from schemas import MemoryItem
from llm_gateway import gateway
from logger import get_logger

log = get_logger("api")

app = FastAPI(title="RAG Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event broadcast for dashboard
import asyncio
event_subscribers: list[asyncio.Queue] = []

def broadcast_event(event: dict):
    for q in event_subscribers:
        q.put_nowait(event)


class IndexRequest(BaseModel):
    url: str
    title: str
    content: str


class QueryRequest(BaseModel):
    query: str
    stream: bool = False


async def fetch_page_content(url: str) -> str:
    """Fetch and extract text from a URL server-side (handles PDFs, blocked pages)."""
    import httpx
    try:
        # For arxiv PDFs, use the HTML version (full paper text)
        if "arxiv.org/pdf/" in url:
            url = url.replace("/pdf/", "/html/").replace(".pdf", "")
        elif "arxiv.org/abs/" in url:
            url = url.replace("/abs/", "/html/")

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; RAGAssistant/1.0)"})
            resp.raise_for_status()
            html = resp.text

            try:
                from readability import Document
                from markdownify import markdownify as md
                doc = Document(html)
                clean_html = doc.summary()
                text = md(clean_html, heading_style="ATX", strip=["img", "svg"])
                title = doc.title()
                return f"# {title}\n\n{text}" if title else text
            except ImportError:
                import re
                text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                return text
    except Exception as e:
        return f"Error fetching {url}: {e}"


@app.post("/index")
async def index_page(req: IndexRequest):
    """Chunk and index a webpage into FAISS."""
    content = req.content

    # Server-side fetch when client couldn't extract content (PDFs, etc.)
    if content == "__FETCH_URL__" or len(content.split()) < 20:
        content = await fetch_page_content(req.url)
        if content.startswith("Error"):
            return {"error": content, "chunks": 0}

    words = content.split()
    if len(words) < 20:
        return {"error": "Page has too little content", "chunks": 0}

    chunk_size = 400
    overlap = 80
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_text = " ".join(words[start:end])
        chunks.append(chunk_text)
        start += chunk_size - overlap

    run_id = uuid.uuid4().hex[:8]
    source_label = f"web:{req.url}"

    import faiss
    from llm_gateway.gateway import EMBED_DIMENSION

    # Batch: embed all chunks, then write to FAISS once
    items_to_add = []
    for i, chunk_text in enumerate(chunks):
        descriptor = f"[{req.title} chunk {i+1}/{len(chunks)}] {chunk_text[:100]}"
        keywords = list(set(
            w.lower().strip(".,!?;:'\"()-[]{}/@#$%^&*")
            for w in chunk_text.split()[:30]
            if len(w) > 3
        ))[:8]
        embedding = gateway.embed(descriptor, task_type="retrieval_document")
        item = MemoryItem(
            id=f"mem_{uuid.uuid4().hex[:12]}",
            kind="fact",
            keywords=[k.lower() for k in keywords],
            descriptor=descriptor,
            value={"chunk": chunk_text, "source": source_label, "title": req.title, "chunk_index": i, "total_chunks": len(chunks)},
            embedding=embedding,
            source=source_label,
            run_id=run_id,
        )
        items_to_add.append(item)

    # Batch write to memory.json
    memory._load()
    memory._items.extend(items_to_add)
    memory._save()

    # Batch write to FAISS index
    index, ids = memory._load_faiss_index()
    if index is None:
        index = faiss.IndexFlatIP(EMBED_DIMENSION)
        ids = []
    vecs_to_add = []
    for item in items_to_add:
        if item.embedding:
            vec = np.array([item.embedding], dtype="float32")
            faiss.normalize_L2(vec)
            vecs_to_add.append(vec)
            ids.append(item.id)
    if vecs_to_add:
        batch = np.vstack(vecs_to_add)
        index.add(batch)
        memory._save_faiss_index(index, ids)

    log.info("page_indexed", url=req.url[:80], chunks=len(chunks))
    return {"status": "indexed", "chunks": len(chunks), "title": req.title}


@app.post("/query")
async def query_knowledge(req: QueryRequest):
    """Answer a question from the FAISS-indexed knowledge base."""
    broadcast_event({'type': 'query_start', 'query': req.query})
    hits = memory.read(req.query, [], kinds=["fact"], top_k=12)

    if not hits:
        # No indexed content matches — fall back to general LLM chat
        from fastapi.responses import StreamingResponse

        broadcast_event({'type': 'step', 'step': 'memory.read', 'detail': 'FAISS search → 0 hits. Falling back to general LLM chat.'})

        messages = [
            {"role": "system", "content": "You are a helpful assistant. Answer concisely using markdown formatting."},
            {"role": "user", "content": req.query},
        ]

        def general_stream():
            yield f"data: {json.dumps({'type': 'step', 'step': 'memory.read', 'detail': 'FAISS search → 0 hits. Falling back to general chat.'})}\n\n"
            yield f"data: {json.dumps({'type': 'step', 'step': 'decision', 'detail': 'No indexed content found — answering from LLM general knowledge'})}\n\n"
            broadcast_event({'type': 'step', 'step': 'decision', 'detail': 'No indexed content — general LLM chat'})
            for chunk in gateway.chat_stream(messages=messages, temperature=0.3):
                evt = {'type': 'token', 'text': chunk}
                broadcast_event(evt)
                yield f"data: {json.dumps(evt)}\n\n"
            done_evt = {'type': 'done'}
            broadcast_event(done_evt)
            yield f"data: {json.dumps(done_evt)}\n\n"

        return StreamingResponse(general_stream(), media_type="text/event-stream")

    # Detect comparison/multi-entity queries
    compare_keywords = ["compare", "difference", "vs", "versus", "contrast", "between"]
    is_comparison = any(kw in req.query.lower() for kw in compare_keywords)

    # Get unique sources from hits
    hit_sources = set(h.value.get("source", "") for h in hits)

    if not is_comparison and len(hit_sources) == 1:
        # Single-source query — return ALL chunks from that source for full context
        top_source = list(hit_sources)[0]
        all_chunks = memory.filter(kinds=["fact"])
        source_chunks = [h for h in all_chunks if h.value.get("source") == top_source]
        source_chunks.sort(key=lambda h: h.value.get("chunk_index", 0))
        context_parts = [h.value.get("chunk", h.descriptor) for h in source_chunks]
        sources = {top_source}
    else:
        # Multi-source or comparison query — pull from ALL mentioned sources
        all_chunks = memory.filter(kinds=["fact"])
        context_parts = []
        sources = set()
        for src in hit_sources:
            src_chunks = [h for h in all_chunks if h.value.get("source") == src]
            src_chunks.sort(key=lambda h: h.value.get("chunk_index", 0))
            title = src_chunks[0].value.get("title", src) if src_chunks else src
            for h in src_chunks:
                context_parts.append(f"[{title}]: {h.value.get('chunk', h.descriptor)}")
            sources.add(src)

    context = "\n\n---\n\n".join(context_parts)

    # Ask LLM to synthesize
    messages = [
        {"role": "system", "content": "You are a research assistant. Answer the user's question using ONLY the provided context. Use markdown formatting. Be concise but comprehensive — cover the key points. Max 300 words."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {req.query}"},
    ]

    from fastapi.responses import StreamingResponse

    sources_list = list(sources)

    # Build retrieval log for transparency
    import re as _re
    retrieval_log = []
    for h in hits[:8]:
        chunk_text = h.value.get("chunk", h.descriptor)[:250]
        # Clean LaTeX artifacts
        chunk_text = _re.sub(r'[𝑚𝑛𝑟𝑙𝑘𝑑𝑥𝑦𝑤𝑏𝑎𝑐𝑒𝑓𝑔ℎ𝑖𝑗𝑜𝑝𝑞𝑠𝑡𝑢𝑣𝑧]+', '', chunk_text)
        chunk_text = _re.sub(r'italic_\w+', '', chunk_text)
        chunk_text = _re.sub(r'\s{2,}', ' ', chunk_text).strip()
        retrieval_log.append({
            "source": h.value.get("title", h.value.get("source", "")),
            "chunk": chunk_text,
            "chunk_index": h.value.get("chunk_index", "?"),
            "total_chunks": h.value.get("total_chunks", "?"),
        })

    def generate():
        # Step 1: Memory read via FAISS
        step1 = {'type': 'step', 'step': 'memory.read', 'detail': f'FAISS vector search → {len(hits)} hits (cosine similarity, 768-d nomic-embed-text)'}
        broadcast_event(step1)
        yield f"data: {json.dumps(step1)}\n\n"

        # Step 2: Retrieval details
        retrieval_evt = {'type': 'retrieval', 'method': 'FAISS vector search (cosine similarity)', 'hits': len(hits), 'sources': sources_list, 'chunks': retrieval_log}
        broadcast_event(retrieval_evt)
        yield f"data: {json.dumps(retrieval_evt)}\n\n"

        # Step 3: Perception
        if is_comparison:
            goal_text = f"Synthesize comparison across {len(sources_list)} sources"
        else:
            goal_text = f"Answer from indexed content ({len(context_parts)} chunks from {list(sources_list)[0].split('/')[-1] if sources_list else '?'})"
        step3 = {'type': 'step', 'step': 'perception', 'detail': f'Goal: {goal_text}'}
        broadcast_event(step3)
        yield f"data: {json.dumps(step3)}\n\n"

        # Step 4: Decision → LLM synthesis
        step4 = {'type': 'step', 'step': 'decision', 'detail': 'Synthesizing answer from retrieved chunks via LLM...'}
        broadcast_event(step4)
        yield f"data: {json.dumps(step4)}\n\n"

        # Step 5: Stream LLM response
        for chunk in gateway.chat_stream(messages=messages, temperature=0.3):
            evt = {'type': 'token', 'text': chunk}
            broadcast_event(evt)
            yield f"data: {json.dumps(evt)}\n\n"

        done_evt = {'type': 'done'}
        broadcast_event(done_evt)
        yield f"data: {json.dumps(done_evt)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/remove")
async def remove_source(req: QueryRequest):
    """Remove all chunks from a specific source."""
    import faiss
    from llm_gateway.gateway import EMBED_DIMENSION

    source_query = req.query.lower()
    memory._load()

    # Find items to keep
    kept = [i for i in memory._items if source_query not in i.value.get("source", "").lower() and source_query not in i.value.get("title", "").lower()]
    removed_count = len(memory._items) - len(kept)

    if removed_count == 0:
        return {"status": "not_found", "message": f"No chunks found matching '{req.query}'"}

    # Rebuild memory and FAISS with only kept items
    memory._items = kept
    memory._save()

    # Rebuild FAISS index from remaining facts with embeddings
    index = faiss.IndexFlatIP(EMBED_DIMENSION)
    ids = []
    for item in kept:
        if item.embedding and item.kind == "fact":
            vec = np.array([item.embedding], dtype="float32")
            faiss.normalize_L2(vec)
            index.add(vec)
            ids.append(item.id)
    memory._save_faiss_index(index, ids)

    return {"status": "removed", "removed": removed_count, "remaining": len(kept)}


@app.post("/new")
async def new_session():
    """Simulate a fresh process — reload memory from disk (persisted FAISS stays intact)."""
    memory._load()
    facts = [i for i in memory._items if i.kind == "fact" and i.value.get("chunk")]
    return {"status": "new_session", "persisted_chunks": len(facts), "total_items": memory.item_count}


@app.post("/clear")
async def clear_state():
    """Clear all indexed data and FAISS index."""
    memory.clear()
    return {"status": "cleared"}


@app.get("/events")
async def event_stream():
    """SSE stream for dashboard — receives all query pipeline events."""
    from fastapi.responses import StreamingResponse

    queue = asyncio.Queue()
    event_subscribers.append(queue)

    async def generate():
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_subscribers.remove(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/agent")
async def agent_query(req: QueryRequest):
    """Run the full agent loop (Perception → Decision → Action) with streaming logs."""
    from fastapi.responses import StreamingResponse
    import asyncio as _asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import action
    import decision
    import perception
    from artifacts import artifact_store
    from config import settings
    from schemas import Goal, SYNTHESIS_KEYWORDS

    broadcast_event({'type': 'query_start', 'query': req.query})

    async def run_agent():
        run_id = uuid.uuid4().hex[:8]
        history = []
        prior_goals = []

        memory._load()
        mem_item = memory.remember(req.query, source="user_query", run_id=run_id)
        if mem_item:
            remember_evt = {'type': 'step', 'step': 'memory', 'detail': f'memory.remember() → stored [{mem_item.kind}] {mem_item.descriptor[:60]}'}
            broadcast_event(remember_evt)
            yield f"data: {json.dumps(remember_evt)}\n\n"
        else:
            remember_evt = {'type': 'step', 'step': 'memory', 'detail': f'memory.remember() → skipped (action query, not a personal fact)'}
            broadcast_event(remember_evt)
            yield f"data: {json.dumps(remember_evt)}\n\n"

        server_params = StdioServerParameters(command="python", args=["mcp_server.py"], env={**__import__("os").environ, "MCP_LOG_LEVEL": "error"})
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                mcp_tools = [{"name": t.name, "description": t.description or "", "parameters": t.inputSchema or {"type": "object", "properties": {}}} for t in result.tools]

                for it in range(1, settings.max_iterations + 1):
                    # Memory read
                    hits = memory.read(req.query, history)
                    source_label = " (FAISS)" if memory._last_read_source == "faiss" else ""
                    step_evt = {'type': 'step', 'step': 'memory', 'detail': f'Iter {it}: memory.read() → {len(hits)} hits{source_label}'}
                    broadcast_event(step_evt)
                    yield f"data: {json.dumps(step_evt)}\n\n"

                    # Perception
                    if len(history) > 0 or it == 1:
                        obs = perception.observe(req.query, hits, history, prior_goals, run_id)
                        prior_goals = obs.goals

                    goals_text = "\n".join(f"  {'✓' if g.done else '→'} {g.text}" for g in obs.goals)
                    perc_evt = {'type': 'step', 'step': 'perception', 'detail': f'Goals:\n{goals_text}'}
                    broadcast_event(perc_evt)
                    yield f"data: {json.dumps(perc_evt)}\n\n"

                    if obs.all_done:
                        # If no answer yet, ask Decision to produce one
                        if not any(e.get("kind") == "answer" for e in history):
                            last_goal = obs.goals[-1]
                            out = decision.next_step(last_goal, hits, [], history, mcp_tools)
                            if out.is_answer:
                                history.append({"iter": it, "kind": "answer", "goal_id": last_goal.id, "text": out.answer})
                                ans_evt = {'type': 'step', 'step': 'decision', 'detail': f'ANSWER: {out.answer[:80]}...'}
                                broadcast_event(ans_evt)
                                yield f"data: {json.dumps(ans_evt)}\n\n"
                            else:
                                # Decision didn't answer — generate summary from actions
                                actions = [e for e in history if e.get("kind") == "action"]
                                if actions:
                                    action_summary = "\n".join(f"- {a.get('tool')}: {a.get('result_descriptor','')[:200]}" for a in actions)
                                    summary_messages = [
                                        {"role": "system", "content": "Summarize what was accomplished in a brief confirmation. Use markdown. No emojis. No internal details."},
                                        {"role": "user", "content": f"Request: {req.query}\n\nActions:\n{action_summary}"},
                                    ]
                                    summary_resp = gateway.chat(messages=summary_messages, temperature=0.3)
                                    if summary_resp.text:
                                        history.append({"iter": it, "kind": "answer", "goal_id": last_goal.id, "text": summary_resp.text})
                                        ans_evt = {'type': 'step', 'step': 'decision', 'detail': f'ANSWER: {summary_resp.text[:80]}...'}
                                        broadcast_event(ans_evt)
                                        yield f"data: {json.dumps(ans_evt)}\n\n"
                        done_evt = {'type': 'step', 'step': 'done', 'detail': f'All {len(obs.goals)} goals satisfied'}
                        broadcast_event(done_evt)
                        yield f"data: {json.dumps(done_evt)}\n\n"
                        break

                    goal = obs.next_unfinished()
                    if goal is None:
                        break

                    # Attachments
                    attached = []
                    goal_lower = goal.text.lower()
                    is_synthesis = any(kw in goal_lower for kw in SYNTHESIS_KEYWORDS)
                    if is_synthesis:
                        for event in history:
                            art_id = event.get("artifact_id")
                            if art_id and artifact_store.exists(art_id):
                                attached.append((art_id, artifact_store.get_bytes(art_id)))
                    elif goal.attach_artifact_id and artifact_store.exists(goal.attach_artifact_id):
                        attached.append((goal.attach_artifact_id, artifact_store.get_bytes(goal.attach_artifact_id)))

                    # Decision — when artifacts are attached, clear memory hits to avoid
                    # hallucination from descriptors that aren't in the artifact content
                    decision_hits = [] if attached else hits
                    out = decision.next_step(goal, decision_hits, attached, history, mcp_tools)

                    if out.is_error:
                        err_evt = {'type': 'step', 'step': 'decision', 'detail': f'Transient error, retrying...'}
                        broadcast_event(err_evt)
                        yield f"data: {json.dumps(err_evt)}\n\n"
                        continue

                    if out.is_answer:
                        # Emit retrieval showing what was ACTUALLY used for this answer
                        # This includes attached artifacts (search_knowledge results)
                        retrieval_log = []
                        hit_sources_set = set()

                        # First: chunks from attached artifacts (what Decision actually read)
                        if attached:
                            for art_id, blob in attached:
                                art_text = blob.decode("utf-8", errors="replace")
                                # Parse search_knowledge format: [source chunk N/M]\ncontent\n\n---\n\n
                                for chunk_block in art_text.split("\n\n---\n\n"):
                                    import re as _re
                                    source_match = _re.match(r'\[(.*?)\s+chunk\s+(\d+)/(\d+)\]', chunk_block)
                                    if source_match:
                                        source = source_match.group(1)
                                        idx = source_match.group(2)
                                        total = source_match.group(3)
                                        chunk_content = _re.sub(r'^\[.*?\]\n', '', chunk_block)
                                        hit_sources_set.add(source)
                                        retrieval_log.append({
                                            "source": source,
                                            "kind": "fact",
                                            "chunk": chunk_content,
                                            "chunk_index": idx,
                                            "total_chunks": total,
                                        })

                        # Fallback: if no attached artifacts, show memory.read fact hits
                        if not retrieval_log:
                            fact_hits_for_display = [h for h in hits if h.kind == "fact" and h.value.get("chunk")]
                            for h in fact_hits_for_display[:6]:
                                hit_sources_set.add(h.value.get("source", h.source))
                                retrieval_log.append({
                                    "source": h.value.get("title", h.value.get("source", h.source)),
                                    "kind": h.kind,
                                    "chunk": h.value.get("chunk", h.descriptor),
                                    "chunk_index": h.value.get("chunk_index", "?"),
                                    "total_chunks": h.value.get("total_chunks", "?"),
                                })

                        if retrieval_log:
                            retrieval_evt = {'type': 'retrieval', 'hits': len(retrieval_log), 'sources': list(hit_sources_set), 'chunks': retrieval_log}
                            broadcast_event(retrieval_evt)
                            yield f"data: {json.dumps(retrieval_evt)}\n\n"

                        ans_evt = {'type': 'step', 'step': 'decision', 'detail': f'ANSWER: {out.answer[:80]}...'}
                        broadcast_event(ans_evt)
                        yield f"data: {json.dumps(ans_evt)}\n\n"
                        history.append({"iter": it, "kind": "answer", "goal_id": goal.id, "text": out.answer})
                        unfinished = sum(1 for g in obs.goals if not g.done)
                        if unfinished <= 1:
                            break
                        continue

                    # Tool call
                    tool_evt = {'type': 'step', 'step': 'decision', 'detail': f'TOOL: {out.tool_call.name}({json.dumps(out.tool_call.arguments)})'}
                    broadcast_event(tool_evt)
                    yield f"data: {json.dumps(tool_evt)}\n\n"

                    result_text, art_id = await action.execute(session, out.tool_call)
                    memory.record_outcome(tool_call=out.tool_call, result_text=result_text, artifact_id=art_id, run_id=run_id, goal_id=goal.id)
                    history.append({"iter": it, "kind": "action", "goal_id": goal.id, "tool": out.tool_call.name, "arguments": out.tool_call.arguments, "result_descriptor": result_text, "artifact_id": art_id})

                    action_evt = {'type': 'step', 'step': 'action', 'detail': f'{out.tool_call.name} → {result_text[:100]}'}
                    broadcast_event(action_evt)
                    yield f"data: {json.dumps(action_evt)}\n\n"

        # Final answer
        answers = [e["text"] for e in history if e.get("kind") == "answer"]
        if answers:
            final = answers[-1]
        else:
            # No explicit answer — summarize what was accomplished
            actions = [e for e in history if e.get("kind") == "action"]
            if actions:
                action_summary = "\n".join(f"- {a.get('tool')}: {a.get('result_descriptor','')[:200]}" for a in actions)
                summary_messages = [
                    {"role": "system", "content": "Summarize what was accomplished in a brief confirmation message. Use markdown. No emojis."},
                    {"role": "user", "content": f"Original request: {req.query}\n\nActions taken:\n{action_summary}"},
                ]
                summary_resp = gateway.chat(messages=summary_messages, temperature=0.3)
                final = summary_resp.text if summary_resp.text else "Tasks completed."
            else:
                final = "No answer produced."
        yield f"data: {json.dumps({'type': 'token', 'text': final})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        broadcast_event({'type': 'done'})

    return StreamingResponse(run_agent(), media_type="text/event-stream")


@app.get("/file/{path:path}")
async def serve_file(path: str):
    """Serve a sandbox file as plain text."""
    from fastapi.responses import PlainTextResponse
    from pathlib import Path
    filepath = Path("state/sandbox") / path
    if not filepath.exists():
        return PlainTextResponse("File not found", status_code=404)
    return PlainTextResponse(filepath.read_text())


@app.get("/")
async def dashboard():
    """Serve the live pipeline dashboard."""
    from fastapi.responses import HTMLResponse
    from pathlib import Path
    html = Path("dashboard.html").read_text()
    return HTMLResponse(html)


@app.get("/health")
async def health():
    facts = [i for i in memory._items if i.kind == "fact"]
    return {"status": "ok", "indexed_chunks": len(facts), "total_items": memory.item_count}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
