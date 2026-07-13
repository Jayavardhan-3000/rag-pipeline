from dataclasses import dataclass, field
from parser.enums import BlockType
    
@dataclass
class AtomicBlock:
    type: BlockType
    content: str
    page: int
    
@dataclass
class MermaidDiagram:
    previous: str
    previous_embedding: list[float] | None
    content: str
    following: str
    following_embedding: list[float] | None
    
@dataclass
class Section:
    section_id: str
    source: str
    title: str
    heading_path: list[str]
    page: int
    contains_image: bool
    contains_table: bool
    contains_formulas: bool
    blocks: list[AtomicBlock]
    mermaid_diagrams: list[MermaidDiagram]
    
@dataclass
class Chunk:
    content: str
    source: str
    title: str
    heading_path: list[str]
    page: int
    contains_image: bool
    contains_table: bool
    contains_formulas: bool
    mermaid_diagrams: list[MermaidDiagram]