# RAG Pipeline

A production-ready, modular **Retrieval-Augmented Generation (RAG)** pipeline built from scratch in Python — no LangChain, no LlamaIndex. Every stage is hand-rolled and clearly separated, making the internals easy to understand, extend, or swap out.

Built as the retrieval backbone for [DOT](https://github.com/Jayavardhan-3000), an offline AI research assistant.

---

## How It Works

```
.txt documents in /sources
        ↓
  [ Chunker ]          — Splits text into overlapping word-windows with SHA-256 chunk IDs
        ↓
  [ Embedder ]         — Encodes chunks using sentence-transformers (all-MiniLM-L6-v2)
        ↓
  [ Vector Index ]     — Builds a FAISS IndexFlatIP (inner-product / cosine similarity)
        ↓  (persisted to ./vector_store on first run, loaded on subsequent runs)
  [ Retriever ]        — Embeds query, searches FAISS, returns top-K scored chunks
        ↓
  [ Generation ]       — Streams answer from a local Ollama LLM with timing metrics
```

---

## Project Structure

```
rag-pipeline/
├── main.py            # Entry point — wires all stages together
├── chunker.py         # Word-window chunking with configurable size and overlap
├── embedder.py        # Batch embedding via SentenceTransformer
├── vector_index.py    # FAISS index build / save / load with @timer decorators
├── retriever.py       # Query embedding + top-K FAISS search
├── generation.py      # Streaming generation via Ollama with TTFT metrics
├── prompts.py         # System prompt for the LLM
├── chunk_type.py      # TypedDict definition for a Chunk
├── config.py          # Central config (model names, TOP_K, paths)
├── a_timer.py         # Timing decorator used across modules
├── sources/           # Drop your .txt documents here
└── vector_store/      # Auto-created — stores faiss.index and chunks.json
```

---

## Pipeline Stages

### 1. Chunking (`chunker.py`)
Reads all `.txt` files from a given directory and splits each into overlapping word-windows.

- Default `chunk_size = 300` words, `overlap_by = 30` words
- Overlap ensures context isn't lost at chunk boundaries
- Each chunk gets a deterministic SHA-256 ID (`doc_stem_idx_hash8`) for idempotency
- Metadata stored per chunk: `chunk_id`, `chunk_index`, `doc_id`, `source`, `word_count`, `content`

### 2. Embedding (`embedder.py`)
Encodes chunks in batches using `sentence-transformers`.

- Model: `sentence-transformers/all-MiniLM-L6-v2` (fast, 384-dim, great for semantic search)
- Embeddings are L2-normalized (`normalize_embeddings=True`) so cosine similarity equals inner product
- Default batch size: 32

### 3. Vector Index (`vector_index.py`)
Builds and persists a FAISS index for fast nearest-neighbor search.

- Index type: `IndexFlatIP` (exact inner-product search — correct for normalized vectors)
- Saves index + chunk metadata as `faiss.index` and `chunks.json` in `./vector_store`
- On subsequent runs, the saved index is loaded directly — no re-embedding needed
- Key functions wrapped with `@timer` for profiling

### 4. Retrieval (`retriever.py`)
Encodes the user query and runs a FAISS search to find the most semantically similar chunks.

- Returns top-K results (default `TOP_K = 5`) with similarity scores attached
- Skips invalid FAISS indices (`idx == -1`) safely

### 5. Generation (`generation.py`)
Passes retrieved context + query to a local LLM via Ollama and streams the response.

- Uses the structured `[system, user]` message format
- Streams tokens to stdout in real-time
- Reports **total time**, **time to first token (TTFT)**, and **streaming duration**

---

## Configuration (`config.py`)

```python
TOP_K = 5                                        # Number of chunks to retrieve
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # Embedding model
LLM = "dotv1:latest"                             # Ollama model name
VECTOR_STORE = "./vector_store"                  # Persistence directory
```

Change `LLM` to any model you have pulled in Ollama (e.g. `llama3`, `mistral`, `phi3`).

---

## Getting Started

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running locally
- An Ollama model pulled: `ollama pull <model-name>`

### Install

```bash
git clone https://github.com/Jayavardhan-3000/rag-pipeline.git
cd rag-pipeline
pip install -r requirements.txt
```

### Add your documents

Drop `.txt` files into the `sources/` directory:

```bash
cp my_document.txt sources/
```

### Run

```bash
python main.py
```

On first run, the pipeline chunks, embeds, and indexes your documents, then saves the vector store. On all subsequent runs it loads the saved index directly and jumps straight to retrieval.

---

## Requirements

```
sentence-transformers
faiss-cpu
numpy
ollama
torch
```

---

## Design Decisions

**Why no framework?** Building without LangChain or LlamaIndex means every component is explicit and debuggable. There's no magic — you can see exactly how chunks are formed, how embeddings flow into FAISS, and how the prompt is constructed.

**Why `IndexFlatIP`?** Because embeddings are L2-normalized, inner product and cosine similarity are equivalent. `IndexFlatIP` does exact search — no approximation errors, which matters at this scale.

**Why SHA-256 chunk IDs?** Identical text always produces the same ID. This enables deduplication and safe re-indexing without creating ghost chunks.

**Why Ollama?** Fully offline, no API keys, supports swapping models with a single config change.

---

## What's Next

- [ ] Hybrid retrieval (BM25 + dense vectors with RRF fusion)
- [ ] Cross-encoder reranking for precision boost
- [ ] Multi-document support (PDF, DOCX ingestion)
- [ ] REST API wrapper (Flask/FastAPI)
- [ ] LLM-as-judge evaluation loop

---

## Author

**Jayavardhan** · [github.com/Jayavardhan-3000](https://github.com/Jayavardhan-3000)
