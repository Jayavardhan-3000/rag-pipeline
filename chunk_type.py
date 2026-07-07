from dataclasses import dataclass, field
from parser.enums import BlockType
@dataclass
class MermaidDiagram:
    index: int
    content: str

@dataclass
class Chunk:
    Content: str
    Source: str
    Title: str
    Heading_Path: list[str]
    page: int
    contains_image: bool
    contains_table: bool
    contains_formulas: bool
    mermaid_diagrams: list[MermaidDiagram] = field(default_factory=list)
    
@dataclass
class AtomicBlock:
    type: BlockType
    content: str
    page: int
    
@dataclass
class MermaidDiagram:
    block_index: int
    offset: int
    content: str
    
@dataclass
class Section:
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
    
@dataclass
class SplitResult:
    blocks: list[AtomicBlock]
    block_mapping: list[tuple[int, int]]