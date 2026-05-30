# Session 7 — RAG Research Agent

A four-role agentic architecture (Memory, Perception, Decision, Action) with FAISS vector retrieval, built on the Session 6 agent. The agent autonomously searches, fetches, indexes, and answers from a semantic knowledge base.

## Architecture

```
User Query
    |
    v
Memory.read() ---> FAISS vector search (768-d, cosine similarity)
    |                     |
    |               [fallback: keyword overlap]
    v
Perception (decompose goals, track completion)
    |
    v
Decision (select tool or answer from memory)
    |
    v
Action (MCP tool dispatch)
    |
    v
Memory.record_outcome() ---> embed + append to FAISS
```

### Session 7 additions (over Session 6):
1. **Gateway `embed()`** — Ollama nomic-embed-text (primary) + Gemini fallback, 768-d vectors
2. **`MemoryItem.embedding`** — optional field, computed at insert for fact/preference/tool_outcome items
3. **FAISS vector search** — IndexFlatIP with L2-normalized cosine similarity, keyword fallback on cold start
4. **Two new MCP tools** — `index_document` (chunking + indexing) and `search_knowledge` (vector retrieval)

### Architectural integrity:
- Perception's SYSTEM prompt contains **zero MCP tool names** (grep test passes)
- Tool-selection guidance lives in Decision's SYSTEM and tool docstrings
- Decision's `_format_hits` renders `value.chunk` so it can read indexed content directly
- FAISS index reloaded from disk on every call for cross-process consistency

## Corpus Manifest

**Topic:** AI Agent Architectures and Reasoning  
**Articles:** 20 web sources  
**Chunks:** 117 (400-word sliding window, 80-word overlap)  
**FAISS vectors:** 150+ (chunks + tool outcomes + facts)

| # | Source | Chunks |
|---|--------|--------|
| 01 | The Landscape of Emerging AI Agent Architectures | 8 |
| 02 | LLM Agents - Prompt Engineering Guide | 8 |
| 03 | Retrieval Augmented Generation (RAG) | 3 |
| 04 | Chain-of-Thought Reasoning Supercharges Enterprise LLMs | 6 |
| 05 | Chain-of-Thought Prompting | 4 |
| 06 | Resilience of LLM-Based Multi-Agent Collaboration | 2 |
| 07 | How Vector Similarity Search Works | 8 |
| 08 | LLM Fine-Tuning Techniques | 4 |
| 09 | Fine-Tuning with Direct Preference Optimization | 7 |
| 10 | Prompt Engineering Principles for 2024 | 8 |
| 11 | Best Practices for Prompt Engineering (OpenAI) | 1 |
| 12 | Memory for Agentic Systems (Deep Dive) | 5 |
| 13 | Memory Systems for AI Agents | 8 |
| 14 | Keyword Search vs Semantic Search | 7 |
| 15 | LLM Benchmark Categories | 6 |
| 16 | LLM Evaluation Metrics & Benchmarks | 8 |
| 17 | Function Calling and Tool Use | 7 |
| 18 | Function Calling (Hugging Face) | 4 |
| 19 | Knowledge Graph LLM (TigerGraph) | 6 |
| 20 | Enhancing LLMs with Knowledge Graphs | 7 |

Additionally, 5 base papers in `state/sandbox/papers/`:
- attention.md (Transformer/Attention Is All You Need)
- chain_of_thought.md (Chain-of-Thought Prompting)
- react.md (ReAct: Reasoning + Acting)
- dpo.md (Direct Preference Optimization)
- lora.md (LoRA: Low-Rank Adaptation)

## Base Query Traces (A-H)

| Query | Description | Iterations | Result |
|-------|-------------|-----------|--------|
| A | Shannon Wikipedia (artifact + extract) | 2 | PASS |
| B | Tokyo activities + weather (multi-goal) | 4 | PASS |
| C Run 1 | Mom's birthday (remember + create) | 11 | PASS |
| C Run 2 | Recall birthday (cross-run FAISS) | 1 | PASS |
| D | Asyncio synthesis (multi-source) | 6 | PASS |
| E | Index attention.md + extract contributions | 2 | PASS |
| F Run 1 | Index all 5 papers | 7 | PASS |
| F Run 2 | Cross-run recall (fresh process, persisted FAISS) | 2 | PASS |
| G | "Credit assignment" synonym recall | 2 | PASS |
| H | ReAct vs CoT cross-document synthesis | 8 | PASS |

## Custom Query Traces (with vs without corpus)

| # | Query | With Index | Without Index | Semantic? |
|---|-------|-----------|---------------|-----------|
| 1 | "What approaches exist for preventing AI hallucinations during retrieval?" | 4 iters (FAISS) | 7 iters (web) | Yes |
| 2 | "How do modern systems decide which model to route a request to?" | 2 iters (FAISS) | 11 iters (web) | Yes |
| 3 | "What are the tradeoffs between storing agent state in-process versus on disk?" | 2 iters (FAISS) | 1 iter (generic) | Yes |
| 4 | "How do researchers measure whether an LLM truly understands what it generates?" | 3 iters (FAISS) | 12 iters (web) | Yes |
| 5 | "What techniques allow smaller models to match the performance of larger ones?" | 7 iters (FAISS) | 11 iters (web) | Yes |

**Key finding:** With the corpus indexed, queries answer in 2-7 iterations from FAISS vector search with domain-specific grounded answers. Without the corpus, the agent must fall back to web search (7-12 iterations) or provides only generic knowledge without the depth from the indexed sources.

## How to Run

### Prerequisites
```bash
pip install -e .                  # or: uv sync
ollama pull nomic-embed-text      # local embeddings (768-d)
```

### Environment (.env)
```
AWS_BEARER_TOKEN_BEDROCK=your-bedrock-api-key
NVIDIA_API_KEY=your-nvidia-key        # free tier fallback
GEMINI_API_KEY=your-gemini-key        # embedding fallback
TAVILY_API_KEY=your-tavily-key        # web search
```

### Build corpus (one-time)
```bash
python build_corpus.py
```

### Run interactively
```bash
python chat.py              # interactive REPL with iteration traces
python chatbot.py           # web UI at http://localhost:8000
python agent6.py "query"    # one-shot CLI
```

### Test queries
```bash
python chat.py "What do the indexed papers say about agent memory?"
python chat.py "How does DPO compare to RLHF?"
python chat.py "What techniques exist for semantic search?"
```

## File Structure

```
agent7/
├── agent6.py          # Main agent loop
├── chat.py            # Interactive CLI with iteration traces
├── chatbot.py         # Web UI (FastAPI + WebSocket)
├── schemas.py         # MemoryItem with embedding field (S7)
├── memory.py          # FAISS vector search + keyword fallback (S7)
├── perception.py      # Goal decomposition (tool-blind)
├── decision.py        # Tool selection + answer generation
├── action.py          # MCP tool dispatch
├── mcp_server.py      # 11 tools incl. index_document, search_knowledge (S7)
├── config.py          # Settings
├── build_corpus.py    # Corpus builder script
├── llm_gateway/
│   └── gateway.py     # Multi-provider router + embed endpoint (S7)
├── state/
│   ├── memory.json    # Durable memory items
│   ├── index.faiss    # FAISS vector index (768-d, IndexFlatIP)
│   ├── index_ids.json # Parallel ID list for FAISS positions
│   └── sandbox/
│       ├── papers/    # 5 base papers
│       └── research/  # 20 fetched articles (corpus)
└── pyproject.toml
```

## Key Design Decisions

- **Vector-first retrieval**: `memory.read()` embeds the query, searches FAISS, falls back to keyword overlap only when FAISS returns nothing
- **Cross-process consistency**: FAISS index reloaded from disk on every call (MCP subprocess writes, agent process reads)
- **Perception tool-blindness**: Perception never sees tool names; emits intent-level goals; Decision maps to tools
- **Embedding model pinned**: Changing nomic-embed-text invalidates all stored vectors (rebuild via `build_corpus.py`)
- **Sliding window chunking**: 400 words, 80 overlap — conservative default for research papers
- **Graceful degradation**: If embed endpoint unreachable, items persist without vectors; keyword search handles them
