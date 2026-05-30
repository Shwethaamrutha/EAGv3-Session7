"""Backend API for Chrome Extension — indexes pages and answers queries via FAISS."""
from __future__ import annotations

import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory import memory
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


class IndexRequest(BaseModel):
    url: str
    title: str
    content: str


class QueryRequest(BaseModel):
    query: str


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

    for i, chunk_text in enumerate(chunks):
        descriptor = f"[{req.title} chunk {i+1}/{len(chunks)}] {chunk_text[:100]}"
        keywords = list(set(
            w.lower().strip(".,!?;:'\"()-[]{}/@#$%^&*")
            for w in chunk_text.split()[:30]
            if len(w) > 3
        ))[:8]
        memory.add_fact(
            descriptor=descriptor,
            value={"chunk": chunk_text, "source": source_label, "title": req.title, "chunk_index": i, "total_chunks": len(chunks)},
            keywords=keywords,
            source=source_label,
            run_id=run_id,
        )

    log.info("page_indexed", url=req.url[:80], chunks=len(chunks))
    return {"status": "indexed", "chunks": len(chunks), "title": req.title}


@app.post("/query")
async def query_knowledge(req: QueryRequest):
    """Answer a question from the FAISS-indexed knowledge base."""
    hits = memory.read(req.query, [], kinds=["fact"], top_k=8)

    if not hits:
        return {"answer": "No relevant content found. Index some pages first!", "sources": []}

    # Build context from chunks
    context_parts = []
    sources = set()
    for h in hits:
        chunk = h.value.get("chunk", h.descriptor)
        title = h.value.get("title", "")
        source = h.value.get("source", "")
        context_parts.append(f"[{title}]: {chunk}")
        if source:
            sources.add(source)

    context = "\n\n---\n\n".join(context_parts[:5])

    # Ask LLM to synthesize
    messages = [
        {"role": "system", "content": "You are a research assistant. Answer the user's question using ONLY the provided context. Be concise and cite which source each claim comes from. If the context doesn't contain the answer, say so."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {req.query}"},
    ]

    resp = gateway.chat(messages=messages, temperature=0.3)

    if resp.is_error:
        return {"answer": "LLM error — try again.", "sources": list(sources)}

    return {"answer": resp.text, "sources": list(sources)}


@app.get("/health")
async def health():
    facts = [i for i in memory._items if i.kind == "fact"]
    return {"status": "ok", "indexed_chunks": len(facts), "total_items": memory.item_count}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
