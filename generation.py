from time import perf_counter

from groq import Groq
from utils import timer

class LLM:
    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model

    @timer
    def generate_answer(self, prompt: str) -> str:
        start = perf_counter()
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                stream=True
            )
            answer = ""
            first_token_time = None
            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token is None:
                    continue
                if first_token_time is None:
                    first_token_time = perf_counter()
                answer += token
                print(
                    token,
                    end="",
                    flush=True
                )
        except Exception as error:
            raise RuntimeError(f"Groq request failed: {error}")
        end = perf_counter()
        print(f"\nTotal generation time : {end - start:.4f} sec")
        if first_token_time is not None:
            print(
                f"First token latency : "
                f"{first_token_time - start:.4f} sec"
            )
            print(
                f"Streaming time : "
                f"{end - first_token_time:.4f} sec"
            )

        return answer