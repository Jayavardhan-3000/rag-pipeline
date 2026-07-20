"""
Builds a labeled test set (query -> ground-truth chunk_id) from the chunks
already sitting in vector_store/chunks.json, so you don't need to hand-write
queries or re-run the parser.

For each sampled chunk, an LLM is asked to write ONE specific question that
can only be answered using that chunk's content. The chunk_id becomes the
ground-truth label for retrieval evaluation.

Usage:
    export GROQ_API_KEY=...
    python benchmark/generate_testset.py --n 40 --out benchmark/testset.jsonl

Notes:
- Uses Groq (same provider the pipeline already depends on) purely to
  *author* questions -- it is not evaluated here, so this doesn't bias any
  benchmark results.
- Chunks that are too short (headers, references, boilerplate) are skipped.
- Sampling is stratified across sources so both PDFs get covered.
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
from groq import Groq  # noqa: E402

load_dotenv()

QUESTION_PROMPT = """You are building a retrieval test set for a RAG system.

Given the passage below, write exactly ONE specific question that:
- Can be answered using ONLY this passage.
- Is NOT answerable from a generic/other passage on the same topic (be specific -- reference concrete facts, numbers, names, or terms that appear in this exact passage).
- Sounds like a real question a user would type into a search box.

Respond with JSON only, no other text: {{"question": "..."}}

Passage (source: {source}, section: {title}):
\"\"\"
{content}
\"\"\"
"""


def load_chunks(chunks_path: str) -> list[dict]:
    with open(chunks_path) as f:
        return json.load(f)


def stratified_sample(chunks: list[dict], n: int, min_words: int = 25) -> list[dict]:
    usable = [c for c in chunks if len(c["content"].split()) >= min_words]
    by_source = defaultdict(list)
    for c in usable:
        by_source[c["source"]].append(c)

    for bucket in by_source.values():
        random.shuffle(bucket)

    sample, sources = [], list(by_source.keys())
    i = 0
    while len(sample) < min(n, len(usable)):
        bucket = by_source[sources[i % len(sources)]]
        if bucket:
            sample.append(bucket.pop())
        i += 1
        if all(not b for b in by_source.values()):
            break
    return sample


def generate_question(client: Groq, model: str, chunk: dict) -> str | None:
    prompt = QUESTION_PROMPT.format(
        source=chunk["source"], title=chunk["title"], content=chunk["content"][:2000]
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    text = resp.choices[0].message.content.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)["question"]
    except (json.JSONDecodeError, KeyError):
        # Fall back to treating the raw text as the question if the model
        # didn't return clean JSON.
        return text if text else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default="vector_store/chunks.json")
    ap.add_argument("--out", default="benchmark/testset.jsonl")
    ap.add_argument("--n", type=int, default=40, help="number of test questions to generate")
    ap.add_argument("--model", default="llama-3.1-8b-instant")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    import os

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("Set GROQ_API_KEY before running (used to author questions).")

    client = Groq(api_key=api_key)
    chunks = load_chunks(args.chunks)
    sample = stratified_sample(chunks, args.n)
    print(f"Sampled {len(sample)} / {len(chunks)} chunks for question generation.")

    rows = []
    for i, chunk in enumerate(sample, 1):
        question = generate_question(client, args.model, chunk)
        if not question:
            print(f"  [{i}/{len(sample)}] skipped (empty response) chunk_id={chunk['chunk_id']}")
            continue
        rows.append({
            "query": question,
            "chunk_id": chunk["chunk_id"],
            "section_id": chunk["section_id"],
            "source": chunk["source"],
            "title": chunk["title"],
        })
        print(f"  [{i}/{len(sample)}] chunk_id={chunk['chunk_id']} -> {question}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"\nWrote {len(rows)} test queries to {args.out}")


if __name__ == "__main__":
    main()
