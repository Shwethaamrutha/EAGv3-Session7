# ÄXON Demo — Narration Script

## Opening (10 seconds)

"This is ÄXON — a RAG-powered research assistant built on top of the Session 6 four-role agent architecture. It adds FAISS vector retrieval, document indexing, and a Chrome extension that lets you index any webpage and ask questions across your indexed knowledge base."

---

## Part 1: Architecture Overview (20 seconds)

*[Show dashboard at localhost:8080]*

"On the left you can see the pipeline — every query goes through 5 stages:
1. The query gets embedded into a 768-dimensional vector using Gemini's embedding model
2. FAISS searches the index for the most similar chunks using cosine similarity
3. Perception sees what was found and decomposes the query into goals
4. Decision picks the next action — either call a tool or synthesize an answer
5. The answer streams back

The live logs on the right show every step in real-time. Let me demonstrate."

---

## Part 2: Base Queries (3-4 minutes)

### Query A — Web Fetch

*[Type: Fetch https://en.wikipedia.org/wiki/Claude_Shannon...]*

"This is a simple fetch-and-extract query. Watch the iterations — Decision calls fetch_url, gets the Wikipedia page, then extracts the answer. No FAISS involved here since nothing is indexed yet."

*[Wait for answer]*

"Born April 30, 1916. Correct. Two iterations."

---

### Query B — Multi-Goal Decomposition

*[Type: Find 3 family-friendly things to do in Tokyo this weekend. Check Saturday's weather forecast there and tell me which one is most appropriate.]*

"This query needs multiple steps — find activities, check weather, then synthesize a recommendation. Watch Perception decompose it into three goals. Decision calls web_search first to find activities via Tavily which returns full page content. Then it fetches the weather from wttr.in. Finally it picks the best option based on conditions."

*[Wait for answer, point to goals showing checkmarks]*

"Three goals, all satisfied. The agent searched, fetched weather, and made a contextual recommendation. Multi-step reasoning with tool orchestration."

---

### Query C — Memory Persistence

*[Type: My mom's birthday is 15 May 2026...]*

"Now I'm telling it a personal fact. Watch the log — memory.remember fires first, classifies this as a 'fact', and stores it with an embedding in FAISS. Then Decision creates the reminder files."

*[Wait for completion, then type: When is mom's birthday?]*

"One iteration. FAISS found the stored fact instantly — that's vector retrieval working across queries. The birthday was embedded and retrieved semantically."

---

### Query D — Multi-Source Synthesis

*[Type: Search for "Python asyncio best practices", read the top 3 results, and give me a short numbered list of the advice they agree on.]*

"This tests multi-source synthesis. The agent searches with Tavily which returns full article content from multiple sources. Decision reads through them and extracts the common advice across all three. Watch how it synthesizes agreement points — not just copying from one source, but finding what multiple sources agree on."

*[Wait for answer]*

"Three to four common best practices extracted from real web sources. The agent searched, read, and synthesized — all in a few iterations."

---

### Query E — Index and Search

*[Type /clear, then: Index the file papers/attention.md and tell me the three key contributions...]*

"This is where RAG shines. Watch — first iteration calls index_document which chunks the paper into pieces and embeds each one into FAISS. Second iteration, Decision calls search_knowledge to query the index. It retrieves the relevant chunks and synthesizes the answer."

*[Point to Retrieved Chunks tab]*

"You can see exactly which chunks were used — these are the actual text passages that informed the answer."

---

### Query G — Semantic Recall

*[After indexing all papers: Across these papers, how do they handle the credit assignment problem?]*

"This is the strongest demonstration. The phrase 'credit assignment' does NOT appear anywhere in these papers. But FAISS understands semantically that this concept maps to 'reward shaping' in the DPO paper and 'backpropagation through reasoning steps' in the chain-of-thought paper. Pure keyword search would return nothing. Vector search finds it."

*[Point to Retrieved Chunks showing DPO and CoT content]*

---

### Query H — Cross-Document Synthesis

*[Type: Compare how the ReAct paper and the Chain-of-Thought paper differ in their treatment of intermediate reasoning.]*

"This requires pulling content from two different papers and comparing them. Watch — search_knowledge retrieves chunks from both ReAct and CoT papers. Decision reads both and produces a structured comparison. ReAct interleaves reasoning with external actions and observations, while Chain-of-Thought maintains a purely internal linear reasoning chain. The agent attributes each claim to its source paper."

*[Point to Retrieved Chunks showing chunks from both papers]*

"This is cross-document synthesis — the agent doesn't just retrieve, it compares and contrasts across sources."

---

## Part 3: Chrome Extension RAG App (3-4 minutes)

### Indexing Pages

*[Open Chrome extension side panel]*

"The Chrome extension is the RAG application. I can click the plus button on any webpage to index it into FAISS. Let me index 5 research papers on parameter-efficient fine-tuning."

*[Click + on each arxiv page, show dashboard chunk count increasing]*

"Each paper gets chunked into 400-word pieces with 80-word overlap, embedded, and stored. We now have about 50 chunks indexed."

---

### Direct Query

*[In side panel: What are intruder dimensions and why do they cause forgetting?]*

"This is a direct query — the keywords exist in the chunks. Watch the dashboard — FAISS finds chunks from the LoRA Illusion paper, Decision calls search_knowledge, gets the relevant passages, and answers."

*[Point to live logs showing the flow]*

---

### Semantic Query

*[In side panel: How do these methods handle the stability-plasticity dilemma?]*

"Now here's the semantic recall. 'Stability-plasticity dilemma' is a neuroscience term that doesn't appear anywhere in these machine learning papers. But FAISS maps it to the concept of 'forgetting versus learning new tasks' — which the LoRA Illusion paper discusses extensively as 'intruder dimensions causing forgetting'."

*[Point to Retrieved Chunks — show it found relevant content despite different vocabulary]*

"This is why vector retrieval matters. Keyword search would fail here. The embedding model understands the semantic equivalence."

---

### Another Semantic Query

*[In side panel: Which approach gives the best bang for your buck in compute savings?]*

"'Bang for your buck' — colloquial language, not academic vocabulary. But FAISS maps it to discussions about parameter reduction ratios, memory savings, and training efficiency across QDyLoRA and the original LoRA paper."

---

## Part 4: No-Corpus Comparison (30 seconds)

*[Type /clear]*

"Now I've wiped the index. Let me ask the same semantic query again without any indexed content."

*[Type: How do these methods handle the stability-plasticity dilemma?]*

"Without the corpus, the agent falls back to web search — takes multiple iterations, fetches external pages, much slower. With the index, it answered in one to two iterations from FAISS. That's the value of RAG — pre-indexed knowledge gives instant, grounded answers."

---

## Part 5: FAISS Persistence (20 seconds)

*[After re-indexing papers, type /new]*

"The /new command simulates a fresh process restart. The FAISS index persists on disk — 47 chunks still available. Now I can query again and it answers immediately from the persisted index. The knowledge survives across sessions."

---

## Closing (15 seconds)

"To summarize — ÄXON extends the Session 6 agent with:
- FAISS vector search for semantic retrieval
- Gemini embeddings at 768 dimensions
- Two new MCP tools: index_document and search_knowledge
- A Chrome extension for indexing any webpage
- A live pipeline dashboard showing every step

The architecture is intact — Perception is tool-blind, Decision selects tools via docstrings, and the four roles communicate through typed contracts. The embedding model is pinned, the index is persistent, and the keyword fallback handles cold start. Thank you."
