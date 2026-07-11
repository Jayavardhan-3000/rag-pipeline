from copy import deepcopy

from chunk_type import Chunk, Section
from recursive_split import recursive_split

def build_content(blocks) -> str:
    return "\n\n".join(block.content for block in blocks)

def create_chunk(section: Section, blocks) -> Chunk:
    return Chunk(
        content=build_content(blocks),
        source=section.source,
        title=section.title,
        heading_path=deepcopy(section.heading_path),
        page=blocks[0].page,
        contains_image=section.contains_image,
        contains_table=any(block.type.name == "TABLE" for block in blocks),
        contains_formulas=section.contains_formulas,
        section_id=section.section_id
    )

def expand_blocks(section: Section, token_counter, max_tokens: int):
    expanded = []

    for block in section.blocks:
        if token_counter(block.content) <= max_tokens:
            expanded.append(block)
        else:
            expanded.extend(
                recursive_split(
                    block,
                    token_counter,
                    max_tokens
                )
            )
    return expanded

def pack_section(
    section: Section,
    token_counter,
    target_tokens: int = 600,
    max_tokens: int = 800
) -> list[Chunk]:
    blocks = expand_blocks(
        section,
        token_counter,
        max_tokens
    )
    chunks = []
    current_blocks = []
    current_tokens = 0
    for block in blocks:
        tokens = token_counter(block.content)
        if current_blocks and current_tokens + tokens > target_tokens:
            chunks.append(
                create_chunk(
                    section,
                    current_blocks
                )
            )
            current_blocks = []
            current_tokens = 0
        current_blocks.append(block)
        current_tokens += tokens
    if current_blocks:
        chunks.append(
            create_chunk(
                section,
                current_blocks
            )
        )

    return chunks

def pack_sections(
    sections: list[Section],
    token_counter,
    target_tokens: int = 600,
    max_tokens: int = 800
) -> list[Chunk]:
    chunks = []
    for section in sections:
        chunks.extend(
            pack_section(
                section,
                token_counter,
                target_tokens,
                max_tokens
            )
        )

    return chunks