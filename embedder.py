from sentence_transformers import SentenceTransformer
from utils import timer
from chunk_type import Chunk
import torch

class Embedder:
    def __init__(self, model_name : str, token : str):
        self.model = SentenceTransformer(model_name, token)
    @timer
    def embed_chunks(self , metadata: list[Chunk] , batch_size: int = 32 ) -> torch.tensor:
        if not metadata:
            raise ValueError("Given metadata is empty!")
        all_embeddings = []
        texts = [chunk["content"] for chunk in metadata]
        all_embeddings = self.model.encode(texts, normalize_embeddings= True, convert_to_numpy = False, show_progress_bar= False, batch_size=batch_size)
        return all_embeddings