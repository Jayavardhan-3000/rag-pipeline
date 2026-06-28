from pathlib import Path #Using it so I can access all the required format files, can't be done context managers
import hashlib #Need this to maintain idempotency, similar unique_id for similar chunks, gonna use in metadata
import logging
from chunk_type import Chunk
from utils import timer

@timer
def chunking(directory : str, chunk_size : int = 300  , overlap_by :int = 30 ) -> list[Chunk]: #Type annotations, syntax- parameter: type = default
    if overlap_by >= chunk_size:
        raise ValueError("overlap_by must be smaller than chunk_size")
    metadata : list[Chunk] = []
    print("Directory:", directory)
    print("Files found:", list(Path(directory).glob("*.txt")))
    for path in sorted(Path(directory).glob("*.txt")):#Iterate through the iterator
        with path.open("r", encoding = "utf-8") as file: #Opening the file via context manager 
            text = file.read()
            words = text.split()
            step = chunk_size - overlap_by #We need to consider the overlap right! so 800 - 150 = 650
            for idx, start in enumerate(range(0,len(words),step),start = 1):#0 to 800, 650 to(+800) 1450, 1300 to 2100, we are overlapping by 150 words
                chunk_words = words[start:start+chunk_size]
                chunk = " ".join(chunk_words)
                if chunk:
                    #0 to 800, 650 to(+800) 1450, 1300 to 2100, we are overlapping by 150 words
                    hashid = hashlib.sha256(chunk.encode()).hexdigest()[:8] #refer to top imports, sha256 is an algorithm,
                    #parameter should be encoded into bytes, 
                    #hexdigest to covert raw data which was returned into hexadecimal format, atleast we can read it
                    unq_id = f"{path.stem}_{idx}_{hashid}"
                    metadata.append({
                        "chunk_id" : unq_id,
                        "chunk_index": idx,
                        "doc_id"   : path.stem,
                        "source"   : str(path),
                        "word_count": len(chunk_words),
                        "content"  : chunk
                    })
    logging.info(f"Loaded all {len(metadata)} from {directory}")
    print("Metadata length:", len(metadata))
    if not metadata:
        raise ValueError(
        f"No chunks generated. Check directory '{directory}' and ensure .txt files contain text."
    )
    return metadata
