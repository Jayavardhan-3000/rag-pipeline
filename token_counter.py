import tiktoken

ENCODER = tiktoken.encoding_for_model("gpt-4o-mini")

def count_tokens(text: str) -> int:
    return len(ENCODER.encode(text))