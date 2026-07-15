from datastructures import Chunk,Context,MermaidRetrievalResult, RetrievalResult
from config import MAX_DIAGRAMS
from query_analyzer import QueryAnalysis
from utils import timer

#Soon will add token limiting, merging adjacent chunks together and more...
class ContextBuilder:
    @timer
    def build(self, query: str, analysis: QueryAnalysis ,retrieval_results: list[RetrievalResult] ,mermaid_results: list[MermaidRetrievalResult]) -> Context:       
        if not retrieval_results:
            raise ValueError("Retrieval results are empty.")
        chunks = []
        seen_chunks = set()
        for result in retrieval_results:
            if result.chunk.chunk_id in seen_chunks:
                continue
            chunks.append(result.chunk)
            seen_chunks.add(result.chunk.chunk_id)
        diagrams = []
        if analysis.needs_mermaid:
            seen_diagrams = set()
            for result in mermaid_results:
                if result.diagram.content in seen_diagrams:
                    continue
                diagrams.append(result.diagram)
                seen_diagrams.add(result.diagram.content)

        return Context(
            query=query,
            chunks=chunks,
            diagrams=diagrams[:MAX_DIAGRAMS]
        )