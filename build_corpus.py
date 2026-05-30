"""Build a 50+ chunk corpus for the Session 7 RAG assignment.

Topic: "AI Agent Architectures and Reasoning"
Strategy: Fetch 10-15 articles from multiple angles, save to sandbox, index into FAISS.
"""
import asyncio
import os
import sys
import re
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

SANDBOX_DIR = Path("state/sandbox/research")
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_QUERIES = [
    "AI agent architectures LLM tool use 2024",
    "retrieval augmented generation RAG techniques",
    "LLM reasoning chain of thought prompting",
    "multi-agent systems collaboration LLM",
    "vector databases embeddings similarity search",
    "LLM fine tuning RLHF DPO techniques",
    "prompt engineering best practices 2024",
    "AI agent memory and planning systems",
    "semantic search vs keyword search comparison",
    "LLM evaluation benchmarks and metrics",
    "function calling tool use large language models",
    "knowledge graphs and LLM integration",
]


async def search_and_fetch():
    """Search for articles and fetch their content."""
    import httpx
    from tavily import TavilyClient

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if not tavily_key:
        print("ERROR: TAVILY_API_KEY not set")
        return

    client = TavilyClient(api_key=tavily_key)
    fetched_urls = set()
    articles = []

    for i, query in enumerate(SEARCH_QUERIES):
        print(f"\n[{i+1}/{len(SEARCH_QUERIES)}] Searching: {query}")
        try:
            response = client.search(query, max_results=2)
            results = response.get("results", [])
        except Exception as e:
            print(f"  Search failed: {e}")
            continue

        for r in results:
            url = r.get("url", "")
            if url in fetched_urls or not url:
                continue
            fetched_urls.add(url)

            title = r.get("title", "Untitled")
            content = r.get("content", "")

            # Try to fetch full content
            print(f"  Fetching: {title[:60]}...")
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as http:
                    resp = await http.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ResearchAgent/1.0)"})
                    resp.raise_for_status()
                    html = resp.text

                    try:
                        from readability import Document
                        from markdownify import markdownify as md
                        doc = Document(html)
                        clean_html = doc.summary()
                        full_title = doc.title() or title
                        text = md(clean_html, heading_style="ATX", strip=["img", "svg"])
                        text = f"# {full_title}\n\n{text}" if full_title else text
                    except ImportError:
                        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
                        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                        text = re.sub(r"<[^>]+>", " ", text)
                        text = f"# {title}\n\n{text}"

                    text = re.sub(r"\n{3,}", "\n\n", text)
                    text = re.sub(r" {2,}", " ", text)
                    text = text.strip()[:15000]

                    if len(text) > 500:
                        articles.append({"title": title, "url": url, "text": text})
                        print(f"    Got {len(text)} chars")
                    else:
                        # Use snippet from Tavily
                        if len(content) > 200:
                            articles.append({"title": title, "url": url, "text": f"# {title}\n\n{content}"})
                            print(f"    Used snippet ({len(content)} chars)")

            except Exception as e:
                # Fall back to Tavily snippet
                if len(content) > 200:
                    articles.append({"title": title, "url": url, "text": f"# {title}\n\n{content}"})
                    print(f"    Fetch failed, used snippet ({len(content)} chars)")
                else:
                    print(f"    Skipped: {e}")

    return articles


def save_articles(articles):
    """Save articles as markdown files in the sandbox."""
    saved = []
    for i, art in enumerate(articles):
        # Clean filename
        slug = re.sub(r'[^a-z0-9]+', '_', art["title"].lower())[:50].strip('_')
        filename = f"{i+1:02d}_{slug}.md"
        filepath = SANDBOX_DIR / filename

        # Add source metadata at top
        content = f"# {art['title']}\n\nSource: {art['url']}\n\n{art['text']}"
        filepath.write_text(content)
        saved.append(filename)
        print(f"  Saved: {filename} ({len(content)} chars)")

    return saved


def index_all(filenames):
    """Index all saved files into FAISS via memory.add_fact."""
    from memory import memory

    total_chunks = 0
    chunk_size = 400
    overlap = 80

    for fname in filenames:
        filepath = SANDBOX_DIR / fname
        text = filepath.read_text()
        words = text.split()

        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk_text = " ".join(words[start:end])
            chunks.append(chunk_text)
            start += chunk_size - overlap

        rel_path = f"research/{fname}"
        for i, chunk in enumerate(chunks):
            descriptor = f"[sandbox:{rel_path} chunk {i+1}/{len(chunks)}] {chunk[:100]}"
            keywords = list(set(
                w.lower().strip(".,!?;:'\"()-[]{}/@#$%^&*")
                for w in chunk.split()[:30]
                if len(w) > 3
            ))[:8]
            memory.add_fact(
                descriptor=descriptor,
                value={"chunk": chunk, "source": f"sandbox:{rel_path}", "chunk_index": i, "total_chunks": len(chunks)},
                keywords=keywords,
                source=f"sandbox:{rel_path}",
                run_id="corpus_build",
            )
        total_chunks += len(chunks)
        print(f"  Indexed: {fname} -> {len(chunks)} chunks")

    return total_chunks


async def main():
    print("=" * 60)
    print("  Building Research Corpus: AI Agent Architectures")
    print("=" * 60)

    # Step 1: Search and fetch
    print("\n--- Phase 1: Fetching articles ---")
    articles = await search_and_fetch()
    print(f"\nFetched {len(articles)} articles total")

    # Step 2: Save to sandbox
    print("\n--- Phase 2: Saving to sandbox ---")
    filenames = save_articles(articles)
    print(f"\nSaved {len(filenames)} files")

    # Step 3: Index into FAISS
    print("\n--- Phase 3: Indexing into FAISS ---")
    total_chunks = index_all(filenames)
    print(f"\n{'=' * 60}")
    print(f"  CORPUS COMPLETE")
    print(f"  Articles: {len(filenames)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  FAISS index: state/index.faiss")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
