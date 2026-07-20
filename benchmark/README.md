# Lotus Benchmark Suite

Drop this `benchmark/` folder into the repo root (next to `main.py`). It measures
three independent things, because they need different setups and answer
different questions:

| Script | Measures | Needs |
|---|---|---|
| `generate_testset.py` | builds a labeled query set from your existing chunks | `GROQ_API_KEY` |
| `bench_retrieval.py` | recall@k / MRR / nDCG@k for semantic-only, BM25-only, RRF-fused, reranked | `HF_TOKEN`, existing vector store |
| `bench_latency.py` | per-stage wall-clock time (analyze → retrieve → fuse → rerank → mermaid → context → prompt → generation) | `HF_TOKEN` (+ `GROQ_API_KEY` for the generation stage) |
| `bench_generation.py` | LLM-judged faithfulness / answer relevance / context precision | `HF_TOKEN`, `GROQ_API_KEY` |

## Quick start

```bash
cd Lotus-Production-style-RAG-pipeline
pip install -r requirements.txt
python main.py                 # only needed once, to build vector_store/ if it doesn't exist yet

export HF_TOKEN=...
export GROQ_API_KEY=...
python benchmark/run_all.py --n 40
```

This generates 40 test questions, then runs retrieval quality, latency, and
answer-quality benchmarks in sequence, writing:
- `benchmark/testset.jsonl`
- `benchmark/retrieval_results.json`
- `benchmark/latency_results.json`
- `benchmark/generation_results.jsonl`

Run any script standalone too, e.g. `python benchmark/bench_retrieval.py` once
you have a test set.

## Why a test set generator instead of hand-written queries

Retrieval metrics (recall@k, MRR, nDCG) need ground truth: "for query X, chunk
Y is the correct answer." `generate_testset.py` samples chunks that are
already in your `vector_store/chunks.json`, stratified across your source
PDFs, and asks an LLM to write one specific question per chunk. The
chunk it was generated from becomes the label. This is the same idea RAGAS'
`TestsetGenerator` uses, just without the extra dependency.

If you'd rather hand-curate a test set, just write a JSONL file with the same
schema: `{"query": "...", "chunk_id": 12, "section_id": "...", "source": "..."}`
and pass `--testset your_file.jsonl` to the bench scripts.

## Mermaid artifact fix (resolved)

`main.py`'s `build_vector_store` now embeds each diagram's `previous`/
`following` text via `embed_diagram_context()` before `ArtifactStore.save()`
runs, so `previous_embedding`/`following_embedding` are no longer `None` and
`mermaid_retriever.py` can actually score diagrams.

**This only takes effect on a fresh index build.** If your `vector_store/`
was built before the fix, `main.py` will just reload the old
`artifacts.json` (still full of `None` embeddings) via `vector_store_exists()`
without re-running `build_vector_store`. Delete `vector_store/artifacts.json`
(or the whole `vector_store/` folder) and re-run `python main.py` once before
benchmarking, or `bench_retrieval.py`/`bench_latency.py`/`bench_generation.py`
will silently keep testing against the stale, embedding-less artifacts.

One remaining edge case, not a bug: a diagram with no preceding *or*
following paragraph (e.g. sitting directly under a heading) has nothing to
embed, so `mermaid_retriever.py` will still correctly skip it -- there's no
context available to match a query against.

Also note: your current `sources/` corpus (the two attention-mechanism PDFs)
has zero Mermaid diagrams in it (`vector_store/artifacts.json` -> `{}`), so
`bench_generation.py`/manual testing won't exercise this stage at all unless
you add a source document that actually contains ` ```mermaid ` blocks.

## Interpreting results

- **Retrieval**: compare `rrf` vs `reranked` recall@k -- if the reranker isn't
  meaningfully improving recall@5/10 over RRF, it may not be worth its latency
  cost for your corpus size.
- **Latency**: `bench_retrieval.py`'s stage latencies isolate retrieval-only
  cost; `bench_latency.py` gives you the full user-facing latency including
  the LLM call, which usually dominates.
- **Generation**: treat LLM-judge scores as directional, not absolute --
  compare *changes* (e.g. before/after a chunking tweak) rather than reading
  too much into a single run's raw numbers.
