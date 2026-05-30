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

**Corpus:** 5 arxiv papers on parameter-efficient fine-tuning (61 chunks total)
- LoRA (original, 2106.09685)
- LoRA vs Full Fine-tuning: An Illusion of Equivalence (2410.21228)
- LoRA vs Full Fine-Tuning: A Theoretical Perspective (2605.19018)
- QDyLoRA: Quantized Dynamic Low-Rank Adaptation (2402.10462)
- Comparison between PEFT techniques and full fine-tuning (2308.07282)

| # | Query | With Index | Without Index | Semantic? |
|---|-------|-----------|---------------|-----------|
| 1 | "What are intruder dimensions and how do they relate to forgetting in fine-tuned models?" | 1 iter, 15s (FAISS) | 7 iters, ~60s (web search → fetch → index) | Yes — "forgetting" maps to "catastrophic interference" |
| 2 | "How does QDyLoRA handle the rank selection problem differently from standard LoRA?" | 1 iter, 9s (FAISS) | 3 iters, ~30s (web search → fetch) | No — direct keyword match |
| 3 | "What specific evidence shows that LoRA and full fine-tuning learn different solutions in weight space?" | 1 iter, 10s (FAISS) | Web search required | Yes — "different solutions" maps to "intruder dimensions" and "spectral analysis" |
| 4 | "What happens when you scale down intruder dimensions in continual fine-tuning?" | 1 iter, 8s (FAISS) | Web search required | Yes — "scale down" maps to "ablation" and "reduced forgetting" |
| 5 | "According to the comparison paper, which parameter-efficient method performs closest to full fine-tuning on generation tasks?" | 1 iter, 7s (FAISS) | Web search required | No — but answer is paper-specific (can't be guessed) |

**Key finding:** With the corpus indexed, all queries answer in 1 iteration via FAISS vector search. Without the corpus, the agent must search the web, fetch papers, and index them first (3-7 iterations, 30-60s). Queries 1, 3, and 4 demonstrate semantic recall — the query terms don't appear literally in the chunks that answer them.

## How to Run

### Prerequisites
```bash
pip install -e .                  # or: uv sync
ollama pull nomic-embed-text      # local embeddings (768-d)
```

### Environment (.env)
```
NVIDIA_API_KEY=your-nvidia-key        # free tier fallback
GEMINI_API_KEY=your-gemini-key        # embedding fallback
TAVILY_API_KEY=your-tavily-key        # web search
```

### Chrome Extension (RAG App)
```bash
# 1. Start the API server
python api_server.py              # runs on http://localhost:8080

# 2. Load extension in Chrome
#    chrome://extensions → Developer mode → Load unpacked → select chrome_extension/

# 3. Open dashboard in browser
#    http://localhost:8080         # live pipeline visualization

# 4. Use the extension
#    - Click + on any page to index it
#    - Open side panel to chat across indexed pages
#    - Dashboard shows live FAISS retrieval logs
```

### Terminal (Base Queries A-H)
```bash
python chat.py              # interactive REPL with iteration traces
python agent6.py "query"    # one-shot CLI
```

### Commands in extension chat
```
/clear                      # wipe all indexed data and FAISS state
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
