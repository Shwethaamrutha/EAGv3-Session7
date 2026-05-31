# ÄXON — RAG Research Agent

A four-role agentic architecture (Memory, Perception, Decision, Action) with FAISS vector retrieval, built on the Session 6 agent. Includes a Chrome extension for indexing any webpage and a live pipeline dashboard.

## Architecture

```
User Query
    |
    v
memory.remember() ---> classify & store personal facts
    |
    v
memory.read() ---> FAISS vector search (Gemini 768-d, cosine similarity)
    |                     |
    |               [fallback: keyword overlap]
    v
Perception (sees FAISS hits, decomposes goals)
    |
    v
Decision (select tool or answer from retrieved context)
    |
    v
Action (MCP tool dispatch)
    |
    v
memory.record_outcome() ---> stored in memory.json (not FAISS)
```

### Session 7 additions (over Session 6):
1. **Gateway `embed()`** — Gemini embedding-001 primary (better quality), Ollama nomic-embed-text fallback, 768-d vectors
2. **`MemoryItem.embedding`** — optional field, computed at insert for fact items only
3. **FAISS vector search** — IndexFlatIP with L2-normalized cosine similarity, keyword fallback on cold start
4. **Two new MCP tools** — `index_document` (chunking + indexing) and `search_knowledge` (vector retrieval)
5. **Chrome extension** — click + to index any page, side panel chat
6. **Live pipeline dashboard** — real-time iteration logs, retrieved chunks, answer rendering

### Key design decisions:
- **Only `add_fact` writes to FAISS** — tool_outcomes and query classifications stay in keyword search only, keeping the vector index clean
- **Gemini embeddings** — nomic-embed-text had poor ranking quality (wrong chunk ranked first); Gemini ranks correctly
- **Perception/search_knowledge consistency** — both use top_k=5 to prevent hallucination from descriptor/content gaps
- **No truncation** — Decision sees full tool results and chunk content for accurate synthesis
- **Hybrid scoring** — FAISS cosine similarity + keyword overlap boost for edge cases
- **LaTeX cleanup** — strips math artifacts from arxiv papers before chunking

### Architectural integrity:
- Perception's SYSTEM prompt contains **zero MCP tool names** (grep test passes)
- Tool-selection guidance lives in Decision's SYSTEM and tool docstrings
- FAISS index reloaded from disk on every call for cross-process consistency

## Base Query Traces (A-H)

| Query | Description | Iterations | Result |
|-------|-------------|-----------|--------|
| A | Shannon Wikipedia (fetch + extract) | 2 | PASS |
| B | Tokyo activities + weather (multi-goal) | 3 | PASS |
| C Run 1 | Mom's birthday (remember + create) | 4 | PASS |
| C Run 2 | Recall birthday (FAISS retrieval) | 1 | PASS |
| D | Asyncio synthesis (web search + synthesize) | 2 | PASS |
| E | Index attention.md + extract contributions | 3 | PASS |
| F Run 1 | Index all 5 papers | 5 | PASS |
| F Run 2 | Cross-run recall (persisted FAISS) | 2 | PASS |
| G | "Credit assignment" semantic recall | 2 | PASS |
| H | ReAct vs CoT cross-document synthesis | 2 | PASS |

## Custom RAG Queries (with vs without corpus)

**Corpus:** 5 arxiv papers on parameter-efficient fine-tuning (~51 chunks)
- Original LoRA (2106.09685)
- LoRA vs Full Fine-tuning: An Illusion of Equivalence (2410.21228)
- LoRA vs Full Fine-Tuning: A Theoretical Perspective (2605.19018)
- QDyLoRA: Quantized Dynamic Low-Rank Adaptation (2402.10462)
- Comparison between PEFT techniques and full fine-tuning (2308.07282)

| # | Query | With Index | Without Index | Semantic? |
|---|-------|-----------|---------------|-----------|
| 1 | "What rank is sufficient for LoRA adaptation on downstream tasks?" | 1-2 iters (FAISS) | Web search needed | No |
| 2 | "What are intruder dimensions and why do they cause forgetting?" | 1-2 iters (FAISS) | Web search needed | No |
| 3 | "How does dynamic rank selection work during training?" | 1-2 iters (FAISS) | Web search needed | No |
| 4 | "How do these methods handle the stability-plasticity dilemma?" | 1-2 iters (FAISS) | Web search needed | Yes — "stability-plasticity dilemma" not in chunks |
| 5 | "Which approach gives the best bang for your buck in compute savings?" | 1-2 iters (FAISS) | Web search needed | Yes — "bang for your buck" not in chunks |

## How to Run

### Prerequisites
```bash
pip install -e .
ollama pull nomic-embed-text      # fallback embeddings
```

### Environment (.env)
```
GEMINI_API_KEY=your-gemini-key        # primary embeddings + chat fallback
NVIDIA_API_KEY=your-nvidia-key        # chat fallback
TAVILY_API_KEY=your-tavily-key        # web search
```

### Run
```bash
# Start the API server (dashboard + extension backend)
python api_server.py              # http://localhost:8080

# Load Chrome extension
# chrome://extensions → Developer mode → Load unpacked → select chrome_extension/

# Or use terminal interface
python chat.py
```

### Commands (in extension chat or dashboard)
```
/clear     — wipe all indexed data and FAISS state
/new       — simulate fresh process (FAISS persists)
/remove X  — remove chunks matching source X
```

## File Structure

```
agent7/
├── api_server.py          # Backend: /agent, /index, /query, /clear, /events
├── dashboard.html         # Live pipeline dashboard (AXON)
├── chrome_extension/      # Chrome extension (side panel + content script)
├── agent6.py              # Main agent loop (terminal)
├── chat.py                # Interactive CLI with iteration traces
├── schemas.py             # MemoryItem with embedding field
├── memory.py              # FAISS vector search + keyword fallback + add_fact
├── perception.py          # Goal decomposition (tool-blind)
├── decision.py            # Tool selection + answer synthesis
├── action.py              # MCP tool dispatch
├── mcp_server.py          # 11 tools incl. index_document, search_knowledge
├── llm_gateway/gateway.py # Multi-provider router + embed (Gemini/Ollama)
├── config.py              # Settings
├── state/
│   ├── memory.json        # All memory items
│   ├── index.faiss        # FAISS vector index (768-d, IndexFlatIP)
│   ├── index_ids.json     # Parallel ID list
│   └── sandbox/papers/    # 5 base papers for queries E-H
└── traces/                # Query trace logs
```
