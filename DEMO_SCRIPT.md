# ÄXON Demo Script

## Setup (before recording)

```bash
# Terminal 1: Start server
cd /Users/shwethd/Desktop/EAGv3/Session7/agent7
python api_server.py

# Open in browser:
# - Dashboard: http://localhost:8080
# - Chrome extension: reload in chrome://extensions
```

---

## Part 1: Base Queries (A-H) — Dashboard

### Show architecture first
- Point to the pipeline diagram on the left (Embed → FAISS → Perception → Decision → Answer)
- Show "Indexed: 0 chunks" in the header

### Query A: Shannon Wikipedia
```
/clear
Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory.
```
**What to show:** Multiple iterations — fetch_url tool call, then answer. No FAISS hits (clean state).

### Query B: Tokyo Activities + Weather
```
Find 3 family-friendly things to do in Tokyo this weekend. Check Saturday's weather forecast there and tell me which one is most appropriate.
```
**What to show:** Multi-goal decomposition, web_search + fetch_url tools, final recommendation.

### Query C: Memory Persistence
```
My mom's birthday is 15 May 2026. Remember that and create reminders for two weeks before and on the day.
```
**What to show:** memory.remember stores fact, create_file makes .ics files.

Then:
```
When is mom's birthday?
```
**What to show:** 1 iteration — FAISS finds the stored fact, answers instantly.

### Query D: Asyncio Synthesis
```
Search for "Python asyncio best practices", read the top 3 results, and give me a short numbered list of the advice they agree on.
```
**What to show:** web_search with Tavily (full content), synthesis from multiple sources.

### Query E: Index + Extract
```
/clear
Index the file papers/attention.md and tell me what the three key contributions of the Transformer architecture are according to this paper.
```
**What to show:** index_document tool → search_knowledge tool → answer from chunks.

### Query F: Index All + Persistence
```
Index papers/cot.md, papers/dpo.md, papers/lora.md, and papers/react.md.
```
**What to show:** Sequential index_document calls, chunk count growing.

Then:
```
/new
Across the papers I have indexed, what do they say about chain-of-thought reasoning?
```
**What to show:** "/new" simulates fresh process, FAISS persists, search_knowledge finds chunks.

### Query G: Synonym Recall (Semantic)
```
Across these papers, how do they handle the credit assignment problem?
```
**What to show:** "credit assignment" not in any chunk — FAISS finds DPO (reward shaping) and CoT (backpropagation through reasoning) semantically.

### Query H: Cross-Document Synthesis
```
Compare how the ReAct paper and the Chain-of-Thought paper differ in their treatment of intermediate reasoning.
```
**What to show:** search_knowledge returns chunks from both papers, synthesis compares them.

---

## Part 2: Custom RAG Application — Chrome Extension + Dashboard

### Setup
```
/clear
```

### Index 5 arxiv papers (click + on each page):
1. https://arxiv.org/abs/2106.09685 (Original LoRA)
2. https://arxiv.org/abs/2410.21228 (LoRA Illusion of Equivalence)
3. https://arxiv.org/abs/2605.19018 (LoRA Theoretical Perspective)
4. https://arxiv.org/abs/2402.10462 (QDyLoRA)
5. https://arxiv.org/abs/2308.07282 (PEFT vs Full Fine-tuning)

**What to show:** Dashboard chunk count increasing as you click +.

### Custom Query 1 (Direct — Original LoRA)
```
What rank is sufficient for LoRA adaptation on downstream tasks?
```
**What to show:** Retrieved chunks from Original LoRA paper, specific rank findings.

### Custom Query 2 (Direct — LoRA Illusion)
```
What are intruder dimensions and why do they cause forgetting?
```
**What to show:** Chunks from LoRA Illusion paper, specific about intruder dimensions.

### Custom Query 3 (Direct — QDyLoRA)
```
How does dynamic rank selection work during training?
```
**What to show:** Chunks from QDyLoRA paper.

### Custom Query 4 (Semantic — stability-plasticity)
```
How do these methods handle the stability-plasticity dilemma?
```
**What to show:** "stability-plasticity dilemma" NOT in chunks — FAISS maps it to "forgetting" and "intruder dimensions" semantically. This is the key RAG demo moment.

### Custom Query 5 (Semantic — compute savings)
```
Which approach gives the best bang for your buck in compute savings?
```
**What to show:** "bang for your buck" NOT in chunks — FAISS maps to parameter reduction, memory savings across multiple papers.

---

## Part 3: No-Corpus Comparison

```
/clear
How do these methods handle the stability-plasticity dilemma?
```
**What to show:** Without index, agent goes to web search (multiple iterations, slow). Compare with Part 2 Query 4 which answered from FAISS in 1-2 iterations.

---

## Key Demo Points to Narrate

1. **FAISS Vector Search** — Show "Retrieved Chunks" tab with actual chunks used
2. **Semantic Recall** — Queries 4 and 5 use words NOT in the chunks
3. **Persistence** — /new shows index survives process restart
4. **Full Agent Loop** — Iterations visible: Memory → Perception → Decision → Action
5. **Chrome Extension** — Click + to index any page, ask questions in side panel
6. **Dashboard** — Live pipeline visualization synced with extension queries

---

## Troubleshooting

- **"No answer produced"** — Run /clear and try again
- **Stale results** — /clear between different query sets
- **Extension disconnected** — Reload extension in chrome://extensions
- **Server down** — `python api_server.py` in agent7/ directory
- **FAISS empty after /clear** — Re-index papers before RAG queries
