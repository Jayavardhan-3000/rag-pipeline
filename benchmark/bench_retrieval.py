"""
Retrieval-quality benchmark: recall@k / MRR / nDCG@k for each stage of the
pipeline, so you can see how much each stage actually contributes.

    semantic-only  -> Retriever.semantic_retrieve
    bm25-only      -> Retriever.bm25_retrieve
    rrf-fused      -> reciprocal_rank_fusion(semantic, bm25)
    reranked       -> Reranker.rerank(rrf-fused)

Usage:
    export HF_TOKEN=...
    python benchmark/bench_retrieval.py --testset benchmark/testset.jsonl
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from config import MODEL_NAME, TOP_K  # noqa: E402
from embedder import Embedder  # noqa: E402
from reranker import Reranker  # noqa: E402
from retriever import Retriever  # noqa: E402
from rrf import reciprocal_rank_fusion  # noqa: E402
from vector_index import load_index_and_metadata, vector_store_exists  # noqa: E402
from metrics import score_ranking, summarize  # noqa: E402

load_dotenv()


def load_testset(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def ids_of(results) -> list[int]:
    return [r.chunk.chunk_id for r in results]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testset", default="benchmark/testset.jsonl")
    ap.add_argument("--out", default="benchmark/retrieval_results.json")
    ap.add_argument("--top_k", type=int, default=TOP_K)
    ap.add_argument("--rerank_model", default="BAAI/bge-reranker-base")
    args = ap.parse_args()

    if not vector_store_exists():
        raise SystemExit("No vector store found -- run `python main.py` once to build it first.")

    testset = load_testset(args.testset)
    if not testset:
        raise SystemExit(f"{args.testset} is empty -- run generate_testset.py first.")

    index, chunks = load_index_and_metadata()
    embedder = Embedder(model_name=MODEL_NAME, token=os.getenv("HF_TOKEN"))
    retriever = Retriever(embedder=embedder, index=index, chunks=chunks, top_k=args.top_k)
    reranker = Reranker(model_name=args.rerank_model)

    per_method_rows = {"semantic": [], "bm25": [], "rrf": [], "reranked": []}
    latencies = {"semantic": [], "bm25": [], "rrf": [], "reranked": []}

    for i, row in enumerate(testset, 1):
        query, gold = row["query"], row["chunk_id"]

        t0 = time.perf_counter()
        semantic = retriever.semantic_retrieve(query)
        latencies["semantic"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        bm25 = retriever.bm25_retrieve(query)
        latencies["bm25"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        fused = reciprocal_rank_fusion(semantic, bm25)
        latencies["rrf"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        reranked = reranker.rerank(query, fused, final_top_k=None)
        latencies["reranked"].append(time.perf_counter() - t0)

        per_method_rows["semantic"].append(score_ranking(ids_of(semantic), gold))
        per_method_rows["bm25"].append(score_ranking(ids_of(bm25), gold))
        per_method_rows["rrf"].append(score_ranking(ids_of(fused), gold))
        per_method_rows["reranked"].append(score_ranking(ids_of(reranked), gold))

        print(f"[{i}/{len(testset)}] {query[:70]!r}")

    summary = {method: summarize(rows) for method, rows in per_method_rows.items()}
    lat_summary = {
        method: {
            "mean_ms": 1000 * sum(v) / len(v),
            "p95_ms": 1000 * sorted(v)[int(0.95 * (len(v) - 1))],
        }
        for method, v in latencies.items()
    }

    print("\n=== Retrieval quality ===")
    header = ["method", "recall@1", "recall@3", "recall@5", "recall@10", "mrr", "ndcg@5"]
    print("{:<10}{:>10}{:>10}{:>10}{:>11}{:>8}{:>9}".format(*header))
    for method, s in summary.items():
        print("{:<10}{:>10.3f}{:>10.3f}{:>10.3f}{:>11.3f}{:>8.3f}{:>9.3f}".format(
            method, s["recall@1"], s["recall@3"], s["recall@5"], s["recall@10"],
            s["mrr"], s["ndcg@5"]
        ))

    print("\n=== Stage latency (query time) ===")
    for method, lat in lat_summary.items():
        print(f"{method:<10} mean={lat['mean_ms']:.1f}ms  p95={lat['p95_ms']:.1f}ms")

    with open(args.out, "w") as f:
        json.dump({"quality": summary, "latency": lat_summary}, f, indent=2)
    print(f"\nSaved full results to {args.out}")


if __name__ == "__main__":
    main()
