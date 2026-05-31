"""Run all base queries and save traces."""
import httpx
import asyncio
import json
import os

API = "http://localhost:8080"

QUERIES = [
    ("a", "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory."),
    ("b", "Find 3 family-friendly things to do in Tokyo this weekend. Check Saturdays weather forecast there and tell me which one is most appropriate."),
    ("c1", "My moms birthday is 15 May 2026. Remember that and create reminders for two weeks before and on the day."),
    ("c2", "When is moms birthday?"),
    ("d", "Search for Python asyncio best practices, read the top 3 results, and give me a short numbered list of the advice they agree on."),
]

QUERIES_EH = [
    ("e", "Index the file papers/attention.md and tell me what the three key contributions of the Transformer architecture are according to this paper."),
    ("f1", "Index papers/cot.md, papers/dpo.md, papers/lora.md, and papers/react.md."),
    ("f2", "Across the papers I have indexed, what do they say about chain-of-thought reasoning?"),
    ("g", "Across these papers, how do they handle the credit assignment problem?"),
    ("h", "Compare how the ReAct paper and the Chain-of-Thought paper differ in their treatment of intermediate reasoning."),
]


async def run_query(client, name, query):
    r = await client.post(f"{API}/agent", json={"query": query})
    lines = []
    for line in r.text.split("\n"):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if data["type"] == "step":
                    step = data["step"]
                    detail = data["detail"]
                    lines.append(f"[{step}] {detail}")
                elif data["type"] == "token":
                    lines.append(f"\n[ANSWER]\n{data['text']}")
                elif data["type"] == "retrieval":
                    lines.append(f"[retrieval] {data['hits']} chunks from {data.get('sources', [])}")
            except:
                pass
    with open(f"traces/query_{name}.txt", "w") as f:
        f.write(f"QUERY: {query}\n\n")
        f.write("\n".join(lines))
    iters = sum(1 for l in lines if "Iter" in l)
    print(f"  Query {name}: {iters} iterations")


async def main():
    os.makedirs("traces", exist_ok=True)

    async with httpx.AsyncClient(timeout=300) as client:
        # Clear state
        await client.post(f"{API}/clear")
        print("--- Queries A-D (clean state) ---")
        for name, query in QUERIES:
            await run_query(client, name, query)

        # Clear and run E-H
        await client.post(f"{API}/clear")
        print("\n--- Queries E-H (clean state, indexing papers) ---")
        for name, query in QUERIES_EH:
            await run_query(client, name, query)

    print("\nTraces saved in traces/ directory")


if __name__ == "__main__":
    asyncio.run(main())
