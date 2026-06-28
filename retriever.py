import faiss
from chunk_type import Chunk
import numpy as np
from embedder import Embedder
from utils import timer

class Retriever():
    def __init__(self, embedder : Embedder, index : faiss.IndexFlatIP, chunks : list[Chunk], top_k : int):
        self.embedder = embedder
        self.index = index
        self.chunks = chunks
        self.top_k = top_k
    def embed_query(self, query: str):
        return self.embedder.model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
    @timer
    def retrieve(self, query:str) -> list[dict]:
            query_embedding = self.embed_query(query)
            query_vector = np.asarray([query_embedding], dtype= np.float32)
            scores, indices = self.index.search(query_vector, self.top_k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:
                    continue
                chunk = self.chunks[idx]
                results.append({**chunk, "score": float(score)}) 
            return results  