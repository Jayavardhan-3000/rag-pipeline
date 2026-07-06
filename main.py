from chunker import chunking
from embedder import Embedder
from parser import markdown_parser
from vector_index import build_faiss_index,save_index_and_metadata, load_index_and_metadata, vector_store_exists
from retriever import Retriever
from generation import generate_answer
from dotenv import load_dotenv
from config import TOP_K,MODEL_NAME, SOURCES_PATH
import os
import asyncio
load_dotenv()

hf_token = os.getenv("HF_TOKEN")
Parser_API_Key = os.getenv("LLAMA_CLOUD_API_KEY")

async def main():
    parser = markdown_parser.MarkdownParser("sources")
    documents = await parser.parse_directory()
    parser = markdown_parser.Markdown_parser(SOURCES_PATH, Parser_API_Key)
    embedder = Embedder(model_name = MODEL_NAME, token = hf_token)
    if vector_store_exists():
        index, chunks = load_index_and_metadata()
    else:
        parser = markdown_parser.MarkdownParser("sources")
        documents = await parser.parse_directory()
        parser = markdown_parser.Markdown_parser(SOURCES_PATH, Parser_API_Key)
        embedder = Embedder(model_name = MODEL_NAME, token = hf_token)
        chunks = chunking(documents)
        print("Number of chunks:", len(chunks))
        print(chunks[:2])
        embeddings = embedder.embed_chunks(chunks)
        index = build_faiss_index(embeddings)
        save_index_and_metadata(index, chunks)

    retriever = Retriever(embedder = embedder,index = index ,chunks = chunks, top_k = TOP_K)

    query = input("Enter your Query:\n")
    results = retriever.retrieve(query)

    generate_answer(query, results)

if __name__ == "__main__":
    asyncio.run(main())
