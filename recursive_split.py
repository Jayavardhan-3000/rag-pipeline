from copy import deepcopy
from chunk_type import Chunk, MermaidDiagram

def split_chunk(
    chunk: Chunk,
    token_counter,
    target_tokens: int = 600,
    max_tokens: int = 800
) -> list[Chunk]:
    if token_counter(chunk.Content) <= max_tokens:
        return [chunk]
    blocks = chunk.Content.split("\n")
    children = _split_blocks(
        blocks,
        chunk,
        token_counter,
        target_tokens,
        max_tokens,
        0
    )
    return children
def _split_blocks(
    blocks: list[str],
    parent: Chunk,
    token_counter,
    target: int,
    maximum: int,
    offset: int
) -> list[Chunk]:
    text = "\n".join(blocks)
    if token_counter(text) <= maximum:
        child = Chunk(
            Content=text,
            Source=parent.Source,
            Title=parent.Title,
            Heading_Path=deepcopy(parent.Heading_Path),
            page=parent.page,
            contains_image=False,
            contains_table=parent.contains_table,
            contains_formulas=parent.contains_formulas
        )
        for diagram in parent.mermaid_diagrams:
            if offset <= diagram.index < offset + len(blocks):
                child.contains_image = True
                child.mermaid_diagrams.append(
                    MermaidDiagram(
                        index=diagram.index - offset,
                        content=diagram.content
                    )
                )
        return [child]
    mid = len(blocks) // 2
    left = blocks[:mid]
    right = blocks[mid:]
    return (
        _split_blocks(
            left,
            parent,
            token_counter,
            target,
            maximum,
            offset
        )
        +
        _split_blocks(
            right,
            parent,
            token_counter,
            target,
            maximum,
            offset + mid
        )
    )