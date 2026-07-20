# Lotus - Production level RAG Pipeline 

A modular, section-aware document indexing pipeline built for Retrieval-Augmented Generation (RAG). Rather than treating a document as plain text, this project preserves document structure, separates visual artifacts from textual content, and produces retrieval-optimized chunks while maintaining semantic integrity.

---


## Motivation

Most RAG pipelines follow a simple workflow:

```
PDF
    ↓
Extract Text
    ↓
Split Every N Tokens
    ↓
Embed
```



Although simple, this approach introduces several problems:

* Sections are broken arbitrarily.
* Long paragraphs lose semantic continuity.
* Visual artifacts such as Mermaid diagrams are embedded as meaningless text.
* Tables and formulas are often mishandled.
* Multiple diagrams inside the same section cannot be retrieved accurately.

This project approaches document indexing differently.

Instead of viewing a document as one continuous stream of text, it treats the document as a hierarchy of semantic units and indexes them accordingly.

---

# Design Philosophy

This project follows a few fundamental principles.

## Sections are the source of truth

A document is first divided into semantic sections using markdown headings.

Everything else is derived from these sections.

```
Document
    │
    ▼
Section
    ├── Metadata
    ├── Paragraph Blocks
    ├── Visual Artifacts
    └── Structural Information
```

Sections remain intact throughout parsing.

---

## Chunks are retrieval units

Chunks are **not** the document representation.

Chunks exist solely for efficient embedding and retrieval.

```
Section
      │
      ▼
Chunk Packing
      │
      ▼
Chunks
      │
      ▼
Embeddings
```

---

## Artifacts are independent

Visual artifacts should never participate in chunking.

Instead, they are extracted during parsing and stored independently.

Current supported artifact:

* Mermaid Diagrams

Future artifacts may include:

* Images
* SVGs
* Flowcharts
* Tables
* UML Diagrams
* Mathematical Figures

---

## Parsing before optimization

The parser captures the document faithfully.

Optimization happens later.

Parsing should never make decisions based on embedding models or vector databases.

---

# Pipeline

```
PDF
 │
 ▼
LlamaParse
 │
 ▼
Markdown
 │
 ▼
Chunker
 │
 ▼
Sections
 ├──────────────┐
 │              │
 ▼              ▼
Packer      Artifact Store
 │              │
 ▼              ▼
Chunks     artifacts.json
 │
 ▼
Embedder
 │
 ▼
Vector Database
```

---

# Architecture

## Chunker

Responsible for converting parsed markdown into semantic sections.

Responsibilities:

* Detect markdown headings
* Preserve heading hierarchy
* Build paragraph blocks
* Detect tables
* Detect formulas
* Extract Mermaid diagrams
* Generate deterministic section identifiers

Output:

```
list[Section]
```

---

## Recursive Splitter

Large paragraph blocks occasionally exceed embedding limits.

Instead of splitting the entire document, only oversized blocks are recursively divided.

The splitter follows a simple strategy:

1. If the block fits → keep it.
2. Split by lines.
3. If only one line exists, split by words.
4. Continue recursively until every block satisfies the token limit.

The splitter acts as a safety mechanism rather than the primary chunking algorithm.

---

## Packer

The packer converts sections into retrieval chunks.

Responsibilities:

* Expand oversized blocks
* Pack blocks into target token sizes
* Preserve section metadata
* Produce retrieval-ready chunks

The packer does **not** know anything about Mermaid diagrams or artifact selection.

---

## Artifact Store

Artifacts are stored independently from chunks.

Current implementation stores:

```
section_id
    │
    ▼
Mermaid Diagrams
```

Artifacts are serialized into JSON.

Chunks only maintain a reference to the originating section.

---

## Embedder

Chunks are embedded for retrieval.

Artifacts are intentionally excluded from chunk embeddings.

Instead, lightweight embeddings are generated only for the contextual paragraphs surrounding each artifact.

---

## Retriever

Retrieval happens in two stages.

### Stage 1

Retrieve the most relevant chunks using vector similarity.

```
Query
    │
    ▼
Vector Database
    │
    ▼
Top-k Chunks
```

---

### Stage 2

If the user explicitly requests a visual artifact:

* Identify retrieved sections.
* Load corresponding artifacts.
* Compare the query with local contextual embeddings.
* Select the most relevant artifact.

```
Top-k Chunks
      │
      ▼
Artifact Store
      │
      ▼
Local Similarity
      │
      ▼
Best Mermaid Diagram
```

---

# Chunking Strategy

Unlike traditional chunkers, this project does not split text immediately by token count.

Instead:

1. Parse semantic sections.
2. Convert paragraphs into atomic blocks.
3. Preserve tables independently.
4. Extract artifacts.
5. Split only oversized paragraph blocks.
6. Pack blocks into retrieval chunks.

This significantly reduces unnecessary semantic fragmentation.

---

# Mermaid Retrieval

Mermaid diagrams are never embedded directly.

Each diagram stores:

* Previous paragraph
* Following paragraph
* Diagram content

During indexing, lightweight embeddings are generated for the surrounding paragraphs.

During retrieval:

```
Query
     │
     ▼
Previous Paragraph Embedding

Following Paragraph Embedding
```

The resulting similarity scores determine which diagram best answers the user's request.

This avoids embedding diagram syntax while still allowing accurate diagram retrieval.

---

# Section Identifiers

Every section receives a deterministic SHA-256 identifier derived from:

```
source + heading_path
```

Advantages:

* Stable across re-indexing
* No random UUIDs
* Easy artifact lookup
* Consistent references

---

# Directory Structure

```
project/
│
├── parser/
│   ├── parsed_page.py
│   ├── enums.py
│   └── ...
│
├── chunk_type.py
├── chunker.py
├── recursive_split.py
├── packer.py
├── artifact_store.py
├── embedder.py
├── retriever.py
├── vector_store.py
└── indexer.py
```

---

# Why not Token Chunking?

Fixed-size chunking often introduces several issues.

```
Paragraph
──────────────┐
              ▼
        Split Here
```

The resulting chunks frequently lose semantic continuity.

Instead, this project prioritizes preserving natural document structure before considering embedding constraints.

---

# Why Artifacts are Separate

Visual artifacts are fundamentally different from textual knowledge.

Embedding Mermaid syntax rarely provides meaningful semantic information.

By separating artifacts:

* Chunk embeddings remain clean.
* Retrieval quality improves.
* Visual content can evolve independently.
* Future artifact types integrate naturally.

---

# Current Features

* Section-aware parsing
* Paragraph-based atomic blocks
* Recursive fallback splitting
* Token-aware chunk packing
* Heading hierarchy preservation
* Table detection
* Formula detection
* Mermaid extraction
* Artifact serialization
* Deterministic section identifiers

---

# Future Improvements

* Multi-artifact support
* Image retrieval
* SVG artifact support
* Formula rendering
* Adaptive chunk packing
* Parallel indexing
* Incremental indexing
* Metadata-aware retrieval
* Hybrid lexical + vector retrieval
* Cross-document artifact linking

---

# Goals

The objective of this project is not simply to split documents.

The goal is to build a document indexing pipeline that preserves semantic structure, minimizes information loss, and provides a strong foundation for Retrieval-Augmented Generation systems.

Rather than optimizing solely for embedding efficiency, the architecture prioritizes maintainability, extensibility, and faithful representation of the original document.
