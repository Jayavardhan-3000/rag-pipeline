import asyncio
import os
from dotenv import load_dotenv
from artifact_store import ArtifactStore
import chunker
import packer
from config import MODEL_NAME,GROQ_MODEL,TOP_K,FINAL_TOP_K,SOURCES_PATH
from context_builder import ContextBuilder
from embedder import Embedder
from generation import LLM
from mermaid_retriever import MermaidRetriever
from parser.markdown_parser import MarkdownParser
from prompt_builder import PromptBuilder
from query_analyzer import QueryAnalyzer
from reranker import Reranker
from retriever import Retriever
from rrf import reciprocal_rank_fusion
from token_counter import count_tokens
from vector_index import build_faiss_index, load_index_and_metadata, save_index_and_metadata,vector_store_exists

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def build_vector_store(embedder: Embedder):
    parser = MarkdownParser(SOURCES_PATH)
    parsed_pages = await parser.parse_directory()
    sections = chunker.chunker(parsed_pages)
    ArtifactStore.save(sections,"./vector_store/artifacts.json")
    chunks = packer.pack_sections( sections,count_tokens)
    embeddings = embedder.embed_chunks(chunks)
    index = build_faiss_index(embeddings)
    save_index_and_metadata(index,chunks)
    artifact_store = ArtifactStore.load("./vector_store/artifacts.json")
    return index, chunks, artifact_store


async def main():
    embedder = Embedder(model_name=MODEL_NAME,token=HF_TOKEN)
    if vector_store_exists():
        index, chunks = load_index_and_metadata()
        artifact_store = ArtifactStore.load("./vector_store/artifacts.json")
    else:
        index, chunks, artifact_store = await build_vector_store(embedder)
    retriever = Retriever(embedder=embedder,index=index,chunks=chunks,top_k=TOP_K)
    reranker = Reranker(model_name="BAAI/bge-reranker-base")
    analyzer = QueryAnalyzer()
    mermaid_retriever = MermaidRetriever(embedder=embedder,artifact_store=artifact_store)
    context_builder = ContextBuilder()
    prompt_builder = PromptBuilder()
    llm = LLM(api_key=GROQ_API_KEY,model=GROQ_MODEL)
    while True:
        if query.lower() in {"exit", "quit"}:
            break
        try:
            query = input("\nQuery > ").strip()
            if query.lower() in {"exit", "quit"}:
                break
            analysis = analyzer.analyze(query)
            semantic_results, bm25_results = retriever.retrieve(query)
            retrieval_results = reciprocal_rank_fusion(semantic_results,  bm25_results)
            reranked_results = reranker.rerank(query=query,results=retrieval_results, final_top_k=FINAL_TOP_K)
            mermaid_results = mermaid_retriever.retrieve(query=query,  analysis=analysis, retrieval_results=reranked_results)
            context = context_builder.build(query=query, analysis=analysis, retrieval_results=reranked_results,mermaid_results=mermaid_results)
            prompt = prompt_builder.build( context )
            print("\nAnswer:\n")
            llm.generate_answer(prompt)
        except ValueError as error:
            print(f"\nNo relevant results found: {error}\n")
            continue

if __name__ == "__main__":
    asyncio.run(main())