from dataclasses import dataclass
from parser import(BlockType, Metadata)
@dataclass
class Block:
    type : BlockType
    content : str
    metadata: Metadata