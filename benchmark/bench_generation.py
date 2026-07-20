"""
Answer-quality benchmark. Runs the full pipeline for each test query, then
uses an LLM judge to score:
    - faithfulness      (1-5): is the answer grounded in the retrieved context,
                                with no unsupported claims?
    - answer_relevance   (1-5): does the answer actually address the query?
    - context_precision  (1-5): were the retrieved chunks relevant to the query?

By default the judge uses a DIFFERENT Groq model than the generator to reduce
self-grading bias -- override with --judge_model if you'd rather match cost.

Usage:
    export HF_TOKEN=...
    export GROQ_API_KEY=...
    python benchmark/bench_generation.py --testset benchmark/testset.jsonl
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from groq import Groq  # noqa: E402
from artifact_store import ArtifactStore  # noqa: E402
from config import MODEL_NAME, TOP_K, FINAL_TOP_K, GROQ_MODEL  # noqa: E402
from context_builder import ContextBuilder  # noqa: E402
from embedder import Embedder  # noqa: E402
from generation import LLM  # noqa: E402
from mermaid_retriever import MermaidRetriever  # noqa: E402
from prompt_builder import PromptBuilder  # noqa: E402
from query_analyzer import QueryAnalyzer  # noqa: E402
from reranker import Reranker  # noqa: E402
from retriever import Retriever  # noqa: E402
from rrf import reciprocal_rank_fusion  # noqa: E402
from vector_index import load_index_and_metadata, vector_store_exists  # noqa: E402

load_dotenv()

import re
import time
from groq import RateLimitError


def call_with_retry(fn, *args, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except RateLimitError as e:
            wait = 5.0
            m = re.search(r"try again in ([\d.]+)s", str(e))
            if m:
                wait = float(m.group(1)) + 1
            print(f"  Rate limited, waiting {wait:.1f}s (attempt {attempt+1}/{max_retries})...")
            time.sleep(wait)
    raise RuntimeError("Exceeded max retries due to rate limiting")

JUDGE_PROMPT = """You are grading a RAG system's answer. Score strictly.

Question: {query}

Retrieved context given to the model:
\"\"\"
{context}
\"\"\"

Model's answer:
\"\"\"
{answer}
\"\"\"

Score each from 1 (worst) to 5 (best) as integers, and respond with JSON only:
{{
  "faithfulness": <int>,      // Is every claim in the answer supported by the context? 1 = fabricated/unsupported, 5 = fully grounded.
  "answer_relevance": <int>,  // Does the answer address the actual question? 1 = off-topic, 5 = directly answers it.
  "context_precision": <int>, // Was the retrieved context relevant to the question? 1 = irrelevant, 5 = highly relevant.
  "notes": "<one short sentence explaining the scores>"
}}
"""


def judge(client: Groq, model: str, query: str, context_text: str, answer: str) -> dict:
    prompt = JUDGE_PROMPT.format(query=query, context=context_text[:4000], answer=answer[:2000])
    resp = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}], temperature=0.0
    )
    text = resp.choices[0].message.content.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"faithfulness": None, "answer_relevance": None, "context_precision": None, "notes": text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testset", default="benchmark/testset.jsonl")
    ap.add_argument("--out", default="benchmark/generation_results.jsonl")
    ap.add_argument("--judge_model", default="llama-3.1-8b-instant")
    args = ap.parse_args()

    if not vector_store_exists():
        raise SystemExit("No vector store found -- run `python main.py` once to build it first.")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("Set GROQ_API_KEY -- required for both generation and judging.")

    with open(args.testset) as f:
        queries = [json.loads(line)["query"] for line in f if line.strip()]
    if not queries:
        raise SystemExit(f"{args.testset} is empty -- run generate_testset.py first.")

    index, chunks = load_index_and_metadata()
    embedder = Embedder(model_name=MODEL_NAME, token=os.getenv("HF_TOKEN"))
    retriever = Retriever(embedder=embedder, index=index, chunks=chunks, top_k=TOP_K)
    reranker = Reranker(model_name="BAAI/bge-reranker-base")
    analyzer = QueryAnalyzer()
    artifact_store = ArtifactStore.load("./vector_store/artifacts.json")
    mermaid_retriever = MermaidRetriever(embedder=embedder, artifact_store=artifact_store)
    context_builder = ContextBuilder()
    prompt_builder = PromptBuilder()
    llm = LLM(api_key=api_key, model=GROQ_MODEL)
    judge_client = Groq(api_key=api_key)

    results = []
    f_out = open(args.out, "w")
    for i, query in enumerate(queries, 1):
        try:
            analysis = analyzer.analyze(query)
            semantic, bm25 = retriever.retrieve(query)
            fused = reciprocal_rank_fusion(semantic, bm25)
            reranked = reranker.rerank(query, fused, final_top_k=FINAL_TOP_K)
            mermaid_results = mermaid_retriever.retrieve(query=query, analysis=analysis, retrieval_results=reranked)
            context = context_builder.build(query=query, analysis=analysis, retrieval_results=reranked, mermaid_results=mermaid_results)
            prompt = prompt_builder.build(context)
            answer = call_with_retry(llm.generate_answer, prompt)
            context_text = "\n\n".join(c.content for c in context.chunks)
            scores = call_with_retry(judge, judge_client, args.judge_model, query, context_text, answer)
        except ValueError as e:
            print(f"[{i}/{len(queries)}] skipped ({e})")
            continue
        except Exception as e:
            print(f"\nStopped early at [{i}/{len(queries)}] due to: {e}")
            break

        row = {"query": query, "answer": answer, **scores}
        results.append(row)
        f_out.write(json.dumps(row) + "\n")
        f_out.flush()
        print(f"[{i}/{len(queries)}] faithfulness={scores.get('faithfulness')} "
              f"relevance={scores.get('answer_relevance')} "
              f"context_precision={scores.get('context_precision')}")
    f_out.close()

    valid = [r for r in results if r.get("faithfulness") is not None]
    if valid:
        for metric in ("faithfulness", "answer_relevance", "context_precision"):
            avg = sum(r[metric] for r in valid) / len(valid)
            print(f"\nAverage {metric}: {avg:.2f} / 5  (n={len(valid)})")

    print(f"\nSaved per-query results to {args.out}")


if __name__ == "__main__":
    main()
