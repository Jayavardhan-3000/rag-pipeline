from chunk_type import Chunk
from pathlib import Path
import numpy as np
import json
import faiss
import logging
import torch
from utils import timer

@timer
def vector_store_exists(save_dir: str = "./vector_store") -> bool:
    store = Path(save_dir)
    return ((store / "faiss.index").exists() and (store / "chunks.json").exists())

@timer
def build_faiss_index(embeddings : torch.tensor) -> faiss.IndexFlatIP:
    if not embeddings:
        raise ValueError("Metadata couldn't be found!")
    vectors = np.array(embeddings, dtype = "float32")
    dim = len(vectors[0])
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index

@timer
def save_index_and_metadata(index : faiss.IndexFlatIP, chunks : list[Chunk], save_dir:str = './vector_store'):
    Path(save_dir).mkdir(exist_ok = True)
    faiss.write_index(index , f"{save_dir}/faiss.index")
    with open(f"{save_dir}/chunks.json","w") as f:
        json.dump(chunks,f)
    logging.info(f"Successfully saved chunks and vectors in {save_dir}/chunks and {save_dir}/faiss.index respectively")
    
    
def load_index_and_metadata(save_dir:str = "./vector_store") -> tuple:
    index = faiss.read_index(f"{save_dir}/faiss.index")
    with open(f"{save_dir}/chunks.json") as f:
        chunks = json.load(f)
    return index,chunks