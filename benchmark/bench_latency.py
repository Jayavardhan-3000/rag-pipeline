"""
End-to-end latency benchmark. Runs every stage of the pipeline for each test
query and reports mean / p50 / p95 per stage, plus totals.

Usage:
    export HF_TOKEN=...
    export GROQ_API_KEY=...          # omit --skip-generation to include LLM call
    python benchmark/bench_latency.py --testset benchmark/testset.jsonl
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from artifact_store import ArtifactStore  # noqa: E402
from config import MODEL_NAME, TOP_K, FINAL_TOP_K, GROQ_MODEL  # noqa: E402
from context_builder import ContextBuilder  # noqa: E402
from embedder import Embedder  # noqa: E402
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

def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    idx = min(len(s) - 1, int(p * (len(s) - 1)))
    return s[idx]


def report(stage_times: dict[str, list[float]]):
    print("\n{:<20}{:>10}{:>10}{:>10}{:>8}".format("stage", "mean(ms)", "p50(ms)", "p95(ms)", "n"))
    total_mean = 0.0
    for stage, values in stage_times.items():
        if not values:
            continue
        mean = 1000 * sum(values) / len(values)
        p50 = 1000 * percentile(values, 0.50)
        p95 = 1000 * percentile(values, 0.95)
        total_mean += mean
        print(f"{stage:<20}{mean:>10.1f}{p50:>10.1f}{p95:>10.1f}{len(values):>8}")
    print(f"\nSum of stage means (approx. end-to-end): {total_mean:.1f} ms")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testset", default="benchmark/testset.jsonl")
    ap.add_argument("--out", default="benchmark/latency_results.json")
    ap.add_argument("--skip-generation", action="store_true", help="skip the Groq LLM call stage")
    args = ap.parse_args()

    if not vector_store_exists():
        raise SystemExit("No vector store found -- run `python main.py` once to build it first.")

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

    llm = None
    if not args.skip_generation:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            from generation import LLM
            llm = LLM(api_key=api_key, model=GROQ_MODEL)
        else:
            print("GROQ_API_KEY not set -- skipping the generation stage.")

    stage_times: dict[str, list[float]] = defaultdict(list)

    def timed(stage, fn, *a, **kw):
        t0 = time.perf_counter()
        result = fn(*a, **kw)
        stage_times[stage].append(time.perf_counter() - t0)
        return result

    for i, query in enumerate(queries, 1):
        try:
            analysis = timed("query_analyze", analyzer.analyze, query)
            semantic, bm25 = timed("retrieve (semantic+bm25)", retriever.retrieve, query)
            fused = timed("rrf_fuse", reciprocal_rank_fusion, semantic, bm25)
            reranked = timed("rerank", reranker.rerank, query, fused, final_top_k=FINAL_TOP_K)
            mermaid_results = timed(
                "mermaid_retrieve", mermaid_retriever.retrieve,
                query=query, analysis=analysis, retrieval_results=reranked
            )
            context = timed(
                "context_build", context_builder.build,
                query=query, analysis=analysis, retrieval_results=reranked, mermaid_results=mermaid_results
            )
            prompt = timed("prompt_build", prompt_builder.build, context)
            GENERATION_DELAY_SEC = 15  # ~4 calls/minute, safely under 6000 TPM at ~1800 tokens/call
            if llm is not None:
                timed("generation", call_with_retry, llm.generate_answer, prompt)
                time.sleep(GENERATION_DELAY_SEC)
        except ValueError as e:
            print(f"[{i}/{len(queries)}] skipped ({e})")
            continue
        print(f"[{i}/{len(queries)}] {query[:70]!r} done")

    report(stage_times)

    with open(args.out, "w") as f:
        json.dump({k: v for k, v in stage_times.items()}, f, indent=2)
    print(f"\nSaved raw timings to {args.out}")


if __name__ == "__main__":
    main()
