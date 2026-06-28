from chunker import chunking
from embedder import Embedder
from vector_index import build_faiss_index,save_index_and_metadata, load_index_and_metadata, vector_store_exists
from retriever import Retriever
from generation import generate_answer
from dotenv import load_dotenv
from config import TOP_K,MODEL_NAME, SOURCES_PATH
import os

load_dotenv()

hf_token = os.getenv("HF_TOKEN")

embedder = Embedder(model_name = MODEL_NAME, token = hf_token)
if vector_store_exists():
    index, chunks = load_index_and_metadata()
else:
    chunks = chunking(f"{SOURCES_PATH}")
    print("Number of chunks:", len(chunks))
    print(chunks[:2])
    embeddings = embedder.embed_chunks(chunks)
    index = build_faiss_index(embeddings)
    save_index_and_metadata(index, chunks)

retriever = Retriever(embedder = embedder,index = index ,chunks = chunks, top_k = TOP_K)

query = input("Enter your Query:\n")
results = retriever.retrieve(query)

answer = generate_answer(query, results)