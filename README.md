# ÄXON — RAG Research Agent

A four-role agentic architecture (Memory, Perception, Decision, Action) with FAISS vector retrieval, built on the Session 6 agent. Includes a Chrome extension for indexing any webpage and a live pipeline dashboard.

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

### Query A — Shannon Wikipedia (2 iterations)

<details><summary>View trace & screenshots</summary>

```
18:53:46
[memory]
Query: "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory."
18:53:46
[faiss]
Embedding query via Gemini embedding...
18:53:46
[memory]
memory.remember() → skipped (action query, not a personal fact)
Iteration 1
18:53:47
[memory]
Iter 1: memory.read() → 0 hits
18:53:51
[perception]
Goals:
  → Fetch https://en.wikipedia.org/wiki/Claude_Shannon and extract his birth date, death date, and three key contributions to information theory.
18:53:53
[decision]
TOOL: fetch_url({"url": "https://en.wikipedia.org/wiki/Claude_Shannon"})
18:53:57
[action]
fetch_url → [artifact art:067c3fd99a6a0ae8, 80201 bytes] preview: # Claude Shannon - Wikipedia  American mathema
Iteration 2
18:53:57
[memory]
Iter 2: memory.read() → 1 hits
18:54:00
[perception]
Goals:
  → Fetch https://en.wikipedia.org/wiki/Claude_Shannon and extract his birth date, death date, and three key contributions to information theory.
18:54:07
[decision]
ANSWER: **Claude Shannon — Key Facts**

- **Born:** April 30, 1916
- **Died:** February ...
18:54:07
[memory]
Done.
```

![A-1](screenshots/A-1.png)
![A-2](screenshots/A-2.png)

</details>

### Query B — Tokyo Activities + Weather (3 iterations)

<details><summary>View trace & screenshots</summary>

```
[memory]     Iter 1: memory.read() → 0 hits
[decision]   TOOL: web_search({"query": "family-friendly things to do in Tokyo..."})
[action]     web_search → [artifact, 15905 bytes]
[memory]     Iter 2: memory.read() → 2 hits
[decision]   TOOL: fetch_url({"url": "https://wttr.in/Tokyo?format=3"})
[action]     fetch_url → # wttr.in - Weather Report
[memory]     Iter 3: memory.read() → 3 hits
[decision]   ANSWER: Tokyo +20°C sunny. Recommended: outdoor activity...
```

![B-1](screenshots/B-1.png)
![B-2](screenshots/B-2.png)
![B-3](screenshots/B-3.png)

</details>

### Query C — Memory Persistence (Run 1: 4 iters, Run 2: 1 iter)

<details><summary>View trace & screenshots</summary>

```
Run 1:
[memory]     memory.remember() → stored [fact] Mom's birthday May 15, 2026
[decision]   TOOL: create_file({"path": "mom_birthday_reminder_2weeks.ics"...})
[decision]   TOOL: create_file({"path": "mom_birthday_reminder_ontheday.ics"...})

Run 2 (fresh process):
[memory]     Iter 1: memory.read() → 2 hits (FAISS)
[decision]   ANSWER: Your mom's birthday is **May 15, 2026**.
```

![C-1](screenshots/C-1.png)
![C-2](screenshots/C-2.png)
![C-3](screenshots/C-3.png)

</details>

### Query D — Asyncio Synthesis (2 iterations)

<details><summary>View trace & screenshots</summary>

```
[memory]     Iter 1: memory.read() → 0 hits
[decision]   TOOL: web_search({"query": "Python asyncio best practices"})
[action]     web_search → [artifact, 8820 bytes] (full Tavily content)
[memory]     Iter 2: memory.read() → 5 hits
[decision]   ANSWER: **Python asyncio Best Practices (Common Advice Across Sources)**
```

![D-1](screenshots/D-1.png)
![D-2](screenshots/D-2.png)

</details>

### Query E — Index + Extract (3 iterations)

<details><summary>View trace & screenshots</summary>

```
[memory]     Iter 1: memory.read() → 1 hits
[decision]   TOOL: index_document({"path": "papers/attention.md"})
[action]     index_document → Indexed 3 chunks
[memory]     Iter 2: memory.read() → 3 hits (FAISS)
[decision]   TOOL: search_knowledge({"query": "key contributions Transformer architecture"})
[action]     search_knowledge → [sandbox:papers/attention.md chunk 2/3]
[memory]     Iter 3: memory.read() → 3 hits (FAISS)
[decision]   ANSWER: ## Three Key Contributions of the Transformer Architecture
```

![E-1](screenshots/E-1.png)
![E-2](screenshots/E-2.png)
![E-3](screenshots/E-3.png)
![E-4](screenshots/E-4.png)

</details>

### Query F — Index All + Cross-Run (Run 1: 5 iters, Run 2: 2 iters)

<details><summary>View trace & screenshots</summary>

```
Run 1:
[decision]   TOOL: index_document({"path": "papers/cot.md"})     → 2 chunks
[decision]   TOOL: index_document({"path": "papers/dpo.md"})     → 21 chunks
[decision]   TOOL: index_document({"path": "papers/lora.md"})    → 6 chunks
[decision]   TOOL: index_document({"path": "papers/react.md"})   → 2 chunks

Run 2 (/new — fresh process, persisted FAISS):
[memory]     Iter 1: memory.read() → 5 hits (FAISS)
[decision]   TOOL: search_knowledge({"query": "chain-of-thought reasoning..."})
[decision]   ANSWER: ## Chain-of-Thought Reasoning: Synthesis from Indexed Papers
```

![F-1](screenshots/F-1.png)
![F-2](screenshots/F-2.png)
![F-3](screenshots/F-3.png)
![F-4](screenshots/F-4.png)
![F-5](screenshots/F-5.png)
![F-6](screenshots/F-6.png)
![F-7](screenshots/F-7.png)

</details>

### Query G — Semantic Recall: "Credit Assignment" (2 iterations)

<details><summary>View trace & screenshots</summary>

```
[memory]     Iter 1: memory.read() → 5 hits (FAISS)
[decision]   TOOL: search_knowledge({"query": "credit assignment problem"})
[action]     search_knowledge → [sandbox:papers/cot.md chunk 1/2] (backpropagation through reasoning)
[memory]     Iter 2: memory.read() → 5 hits (FAISS)
[decision]   ANSWER: ## Credit Assignment Across the Indexed Papers
```

*Note: "credit assignment" does NOT appear in any chunk. FAISS finds it via semantic similarity to "reward shaping" (DPO) and "backpropagation through reasoning steps" (CoT).*

![G-1](screenshots/G-1.png)
![G-2](screenshots/G-2.png)
![G-3](screenshots/G-3.png)

</details>

### Query H — Cross-Document Synthesis (2 iterations)

<details><summary>View trace & screenshots</summary>

```
[memory]     Iter 1: memory.read() → 5 hits (FAISS)
[decision]   TOOL: search_knowledge({"query": "intermediate reasoning treatment..."})
[action]     search_knowledge → [sandbox:papers/react.md chunk 0/2], [sandbox:papers/cot.md chunk 1/2]
[memory]     Iter 2: memory.read() → 5 hits (FAISS)
[decision]   ANSWER: ## Treatment of Intermediate Reasoning: ReAct vs. Chain-of-Thought
```

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

| # | Query | With Index | Without Index | Semantic? |
|---|-------|-----------|---------------|-----------|
| 1 | "What rank is sufficient for LoRA adaptation on downstream tasks?" | 1-2 iters (FAISS) | Web search needed | No |
| 2 | "What are intruder dimensions and why do they cause forgetting?" | 1-2 iters (FAISS) | Web search needed | No |
| 3 | "How does dynamic rank selection work during training?" | 1-2 iters (FAISS) | Web search needed | No |
| 4 | "How do these methods handle the stability-plasticity dilemma?" | 1-2 iters (FAISS) | Web search needed | Yes — "stability-plasticity dilemma" not in chunks |
| 5 | "Which approach gives the best bang for your buck in compute savings?" | 1-2 iters (FAISS) | Web search needed | Yes — "bang for your buck" not in chunks |

<details><summary>Custom Query 1 — LoRA Rank (Direct)</summary>

![Custom-A1](screenshots/Custom-A1.png)
![Custom-A2](screenshots/Custom-A2.png)
![Custom-A3](screenshots/Custom-A3.png)

</details>

<details><summary>Custom Query 2 — Intruder Dimensions (Direct)</summary>

![Custom-B1](screenshots/Custom-B1.png)
![Custom-B2](screenshots/Custom-B2.png)
![Custom-B3](screenshots/Custom-B3.png)

</details>

<details><summary>Custom Query 3 — QDyLoRA Dynamic Rank (Direct)</summary>

![Custom-C1](screenshots/Custom-C1.png)
![Custom-C2](screenshots/Custom-C2.png)
![Custom-C3](screenshots/Custom-C3.png)

</details>

<details><summary>Custom Query 4 — Theoretical/PEFT (Direct)</summary>

![Custom-D1](screenshots/Custom-D1.png)
![Custom-D2](screenshots/Custom-D2.png)

</details>

<details><summary>Custom Query 5 — Stability-Plasticity Dilemma (Semantic Recall)</summary>

*"Stability-plasticity dilemma" does not appear in any chunk. FAISS maps it semantically to "forgetting" and "intruder dimensions".*

![Custom-E1-Sem](screenshots/Custom-E1-Sem.png)
![Custom-E2-Sem](screenshots/Custom-E2-Sem.png)
![Custom-E3-Sem](screenshots/Custom-E3-Sem.png)

</details>

<details><summary>Custom Query 6 — Compute Savings (Semantic Recall)</summary>

*"Bang for your buck" does not appear in any chunk. FAISS maps it to parameter reduction and memory efficiency discussions.*

![Custom-F1-Sem](screenshots/Custom-F1-Sem.png)
![Custom-F2-Sem](screenshots/Custom-F2-Sem.png)
![Custom-F3-Sem](screenshots/Custom-F3-Sem.png)

</details>

<details><summary>No-Corpus Comparison</summary>

*Same query without indexed content — agent falls back to web search (slower, more iterations):*

![Custom-G1-Nocorpus](screenshots/Custom-G1-Nocorpus.png)

*After indexing — answers from FAISS in 1-2 iterations:*

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
