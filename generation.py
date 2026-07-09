from prompts import SYSTEM_PROMPT 
from ollama import chat
from config import LLM
from time import perf_counter
import httpx
def generate_answer(query: str, retrieved_chunks : list[dict]) -> str:
    start = perf_counter()
    context = "\n\n---\n\n".join(c["content"] for c in retrieved_chunks)
    try:
        stream = chat(
            model=LLM,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"""
            Context:{context}
            Question: {query}
            Answer"""},
            ],
            stream=True,
        )
        first_token_time = None
        answer = ""
        for chunk in stream:
            if first_token_time is None:
                first_token_time = perf_counter()
            token = chunk["message"]["content"]
            answer += token
            print(token , end = "", flush = True)
    except httpx.ConnectError:
        raise RuntimeError(
            "Could not connect to Ollama. Make sure it's running: `ollama serve`"
        )
    except Exception as e:
        raise RuntimeError(f"Ollama failed: {e}")
    end_token_time = perf_counter()
    print(f"\nTotal time taken for the whole answer : {end_token_time - start : .4f} sec")
    print(f"Time taken for the first token : {first_token_time - start : .4f} sec")
    print(f"Time taken for the streaming : {end_token_time - first_token_time : .4f} sec")