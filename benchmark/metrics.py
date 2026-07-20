"""
Standard retrieval metrics for a single-relevant-document setup
(each test query has exactly one ground-truth chunk_id).
"""
import math


def rank_of(ranked_ids: list[int], relevant_id: int) -> int | None:
    """1-indexed rank of the relevant id in the ranked list, or None if absent."""
    try:
        return ranked_ids.index(relevant_id) + 1
    except ValueError:
        return None


def recall_at_k(ranked_ids: list[int], relevant_id: int, k: int) -> int:
    r = rank_of(ranked_ids[:k], relevant_id)
    return 1 if r is not None else 0


def reciprocal_rank(ranked_ids: list[int], relevant_id: int) -> float:
    r = rank_of(ranked_ids, relevant_id)
    return 1.0 / r if r is not None else 0.0


def ndcg_at_k(ranked_ids: list[int], relevant_id: int, k: int) -> float:
    # Single relevant doc => ideal DCG@k = 1 (relevant doc at rank 1).
    r = rank_of(ranked_ids[:k], relevant_id)
    if r is None:
        return 0.0
    return 1.0 / math.log2(r + 1)


def summarize(per_query_rows: list[dict], ks: tuple[int, ...] = (1, 3, 5, 10)) -> dict:
    """Average recall@k / MRR / nDCG@k across queries for one retrieval method."""
    n = len(per_query_rows)
    if n == 0:
        return {}
    out = {"n_queries": n}
    for k in ks:
        out[f"recall@{k}"] = sum(row[f"recall@{k}"] for row in per_query_rows) / n
        out[f"ndcg@{k}"] = sum(row[f"ndcg@{k}"] for row in per_query_rows) / n
    out["mrr"] = sum(row["mrr"] for row in per_query_rows) / n
    return out


def score_ranking(ranked_ids: list[int], relevant_id: int, ks: tuple[int, ...] = (1, 3, 5, 10)) -> dict:
    row = {"mrr": reciprocal_rank(ranked_ids, relevant_id)}
    for k in ks:
        row[f"recall@{k}"] = recall_at_k(ranked_ids, relevant_id, k)
        row[f"ndcg@{k}"] = ndcg_at_k(ranked_ids, relevant_id, k)
    return row
