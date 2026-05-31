# ÄXON

### Semantic Research Agent with FAISS Vector Retrieval

> *Index any webpage. Ask questions across your knowledge. Get answers grounded in what you've read — not what the LLM imagines.*

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FAISS](https://img.shields.io/badge/FAISS-IndexFlatIP-green)](https://github.com/facebookresearch/faiss)
[![Gemini](https://img.shields.io/badge/Embedding-Gemini%20768d-orange)](https://ai.google.dev)
[![Chrome](https://img.shields.io/badge/Chrome-Extension-yellow)](chrome_extension/)

---

**ÄXON** is a four-role agentic architecture (Memory → Perception → Decision → Action) extended with FAISS vector retrieval for semantic search across indexed documents. Built as Session 7 of the [EAG V3](https://theschoolof.ai) program.

**What makes it different:**
- Queries work when your **words don't match** the indexed text (semantic recall)
- A Chrome extension lets you **index any webpage** with one click
- A live dashboard shows **every pipeline step** in real-time
- Knowledge **persists across sessions** via FAISS on disk

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                      │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ░░ MEMORY.REMEMBER ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  Classify query → store personal facts (birthday, preferences)              │
│  Scratchpad items skipped for action queries                                │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ▓▓ MEMORY.READ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │
│                                                                             │
│  ┌─────────────────────┐    ┌──────────────────────────────────────────┐    │
│  │  Embed Query         │    │  FAISS IndexFlatIP                       │    │
│  │  Gemini 768-d        │───▶│  Cosine similarity search                │    │
│  │                      │    │  Top-5 most similar chunks               │    │
│  └─────────────────────┘    └──────────────┬───────────────────────────┘    │
│                                             │                               │
│                              [if no FAISS hits: keyword fallback]            │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ hits (chunk descriptors)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ◆◆ PERCEPTION ◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆◆  │
│  Sees: query + FAISS hits + history                                         │
│  Outputs: ordered goals (✓ done / → open)                                  │
│  Rule: TOOL-BLIND — never sees or names MCP tools                           │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ goals
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ★★ DECISION ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★  │
│  Sees: goal + hits + attached artifacts + history + tool catalog             │
│  Outputs: ANSWER (from context) OR one TOOL CALL                            │
│                                                                             │
│  Tools: web_search | fetch_url | index_document | search_knowledge          │
│         read_file | create_file | list_dir | get_time | ...                  │
└───────────────┬─────────────────────────────────┬───────────────────────────┘
                │ (answer)                         │ (tool call)
                ▼                                  ▼
┌───────────────────────────┐    ┌────────────────────────────────────────────┐
│         ANSWER             │    │  ◈◈ ACTION ◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈  │
│  Streamed to user          │    │  Execute MCP tool via stdio subprocess     │
│                            │    │  Result → memory.record_outcome()          │
└───────────────────────────┘    │  Large results → artifact store            │
                                  └──────────────────────┬───────────────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────────┐
                                              │  NEXT ITERATION      │
                                              │  (loop back to       │
                                              │   memory.read)       │
                                              └──────────────────────┘
```

---

### What Session 7 adds over Session 6:

| Component | Addition |
|-----------|----------|
| Gateway | `embed()` — Gemini 768-d primary, Ollama fallback |
| Schema | `MemoryItem.embedding` — stored at insert for fact items |
| Memory | FAISS IndexFlatIP vector search, keyword fallback |
| MCP Tools | `index_document` (chunk + embed) and `search_knowledge` (vector query) |
| Frontend | Chrome extension + live pipeline dashboard |

### Design decisions that matter:

| Decision | Why |
|----------|-----|
| Only `add_fact` → FAISS | Keeps vector index clean (no tool_outcome noise) |
| Gemini over nomic-embed-text | Correct ranking (nomic put wrong chunk first) |
| top_k=5 everywhere | Perception and search_knowledge see same data (prevents hallucination) |
| No truncation | Decision sees full chunks — was the root cause of search_knowledge loops |
| Hybrid scoring | Cosine similarity + keyword boost for edge cases |

### Architectural rules (carried from Session 6):
- `grep` test: **zero MCP tool names** in Perception's SYSTEM prompt
- Tool-selection guidance lives in Decision's SYSTEM + tool docstrings
- FAISS reloaded from disk on every call (cross-process consistency)

## Base Query Traces (A-H)

| Query | Description | Iterations |
|-------|-------------|-----------|
| A | Shannon Wikipedia (fetch + extract) | 2 |
| B | Tokyo activities + weather (multi-goal) | 3 |
| C Run 1 | Mom's birthday (remember + create files) | 4 |
| C Run 2 | Recall birthday (FAISS retrieval) | 1 |
| D | Asyncio synthesis (web search + synthesize) | 2 |
| E | Index attention.md + extract contributions | 3 |
| F Run 1 | Index all 5 papers | 5 |
| F Run 2 | Cross-run recall (persisted FAISS) | 2 |
| G | "Credit assignment" semantic recall | 2 |
| H | ReAct vs CoT cross-document synthesis | 2 |

<details><summary>View all base query screenshots</summary>

**Query A — Shannon Wikipedia**
![A-1](screenshots/A-1.png)
![A-2](screenshots/A-2.png)

**Query B — Tokyo Activities + Weather**
![B-1](screenshots/B-1.png)
![B-2](screenshots/B-2.png)
![B-3](screenshots/B-3.png)

**Query C — Memory Persistence**
![C-1](screenshots/C-1.png)
![C-2](screenshots/C-2.png)
![C-3](screenshots/C-3.png)

**Query D — Asyncio Synthesis**
![D-1](screenshots/D-1.png)
![D-2](screenshots/D-2.png)

**Query E — Index + Extract**
![E-1](screenshots/E-1.png)
![E-2](screenshots/E-2.png)
![E-3](screenshots/E-3.png)
![E-4](screenshots/E-4.png)

**Query F — Index All + Cross-Run Persistence**
![F-1](screenshots/F-1.png)
![F-2](screenshots/F-2.png)
![F-3](screenshots/F-3.png)
![F-4](screenshots/F-4.png)
![F-5](screenshots/F-5.png)
![F-6](screenshots/F-6.png)
![F-7](screenshots/F-7.png)

**Query G — Semantic Recall ("credit assignment" not in chunks)**
![G-1](screenshots/G-1.png)
![G-2](screenshots/G-2.png)
![G-3](screenshots/G-3.png)

**Query H — Cross-Document Synthesis**
![H-1](screenshots/H-1.png)
![H-2](screenshots/H-2.png)
![H-3](screenshots/H-3.png)

</details>

## Custom RAG Queries (with vs without corpus)

**Corpus:** 5 arxiv papers on parameter-efficient fine-tuning (~51 chunks)
- Original LoRA (2106.09685)
- LoRA vs Full Fine-tuning: An Illusion of Equivalence (2410.21228)
- LoRA vs Full Fine-Tuning: A Theoretical Perspective (2605.19018)
- QDyLoRA: Quantized Dynamic Low-Rank Adaptation (2402.10462)
- Comparison between PEFT techniques and full fine-tuning (2308.07282)

| # | Query | Semantic? |
|---|-------|-----------|
| 1 | "What rank is sufficient for LoRA adaptation on downstream tasks?" | No |
| 2 | "What are intruder dimensions and why do they cause forgetting?" | No |
| 3 | "How does dynamic rank selection work during training?" | No |
| 4 | "How do these methods handle the stability-plasticity dilemma?" | Yes |
| 5 | "Which approach gives the best bang for your buck in compute savings?" | Yes |

<details><summary>View all custom query screenshots</summary>

**Custom Query 1 — LoRA Rank (Direct)**
![Custom-A1](screenshots/Custom-A1.png)
![Custom-A2](screenshots/Custom-A2.png)
![Custom-A3](screenshots/Custom-A3.png)

**Custom Query 2 — Intruder Dimensions (Direct)**
![Custom-B1](screenshots/Custom-B1.png)
![Custom-B2](screenshots/Custom-B2.png)
![Custom-B3](screenshots/Custom-B3.png)

**Custom Query 3 — QDyLoRA Dynamic Rank (Direct)**
![Custom-C1](screenshots/Custom-C1.png)
![Custom-C2](screenshots/Custom-C2.png)
![Custom-C3](screenshots/Custom-C3.png)

**Custom Query 4 — Theoretical/PEFT (Direct)**
![Custom-D1](screenshots/Custom-D1.png)
![Custom-D2](screenshots/Custom-D2.png)

**Custom Query 5 — Stability-Plasticity Dilemma (Semantic Recall)**
![Custom-E1-Sem](screenshots/Custom-E1-Sem.png)
![Custom-E2-Sem](screenshots/Custom-E2-Sem.png)
![Custom-E3-Sem](screenshots/Custom-E3-Sem.png)

**Custom Query 6 — Compute Savings (Semantic Recall)**
![Custom-F1-Sem](screenshots/Custom-F1-Sem.png)
![Custom-F2-Sem](screenshots/Custom-F2-Sem.png)
![Custom-F3-Sem](screenshots/Custom-F3-Sem.png)

**No-Corpus Comparison**
![Custom-G1-Nocorpus](screenshots/Custom-G1-Nocorpus.png)
![Custom-G2-afterIndex](screenshots/Custom-G2-afterIndex.png)
![Custom-G3-afterIndex](screenshots/Custom-G3-afterIndex.png)

</details>


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
