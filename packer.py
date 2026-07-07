from copy import deepcopy

from chunk_type import Chunk, Section, MermaidDiagram
from recursive_split import recursive_split


def build_content(blocks):
    return "\n\n".join(block.content for block in blocks)


def create_chunk(section, blocks, start_index, end_index):
    chunk = Chunk(
        content=build_content(blocks),
        source=section.source,
        title=section.title,
        heading_path=deepcopy(section.heading_path),
        page=blocks[0].page,
        contains_image=False,
        contains_table=any(block.type.name == "TABLE" for block in blocks),
        contains_formulas=section.contains_formulas,
        mermaid_diagrams=[]
    )

    for diagram in section.mermaid_diagrams:
        if start_index <= diagram.block_index < end_index:
            chunk.contains_image = True
            chunk.mermaid_diagrams.append(
                MermaidDiagram(
                    block_index=diagram.block_index - start_index,
                    content=diagram.content
                )
            )

    return chunk


def pack_section(
    section: Section,
    token_counter,
    target_tokens: int = 600,
    max_tokens: int = 800
):
    expanded_blocks = []
    mapping = []

    for index, block in enumerate(section.blocks):
        if token_counter(block.content) <= max_tokens:
            expanded_blocks.append(block)
            mapping.append(index)
        else:
            split_blocks = recursive_split(
                block,
                token_counter,
                max_tokens
            )

            expanded_blocks.extend(split_blocks)
            mapping.extend([index] * len(split_blocks))

    chunks = []

    current_blocks = []
    current_mapping = []
    current_tokens = 0

    for block, original_index in zip(expanded_blocks, mapping):
        block_tokens = token_counter(block.content)

        if current_blocks and current_tokens + block_tokens > target_tokens:
            chunks.append(
                create_chunk(
                    section,
                    current_blocks,
                    current_mapping[0],
                    current_mapping[-1] + 1
                )
            )

            current_blocks = []
            current_mapping = []
            current_tokens = 0

        current_blocks.append(block)
        current_mapping.append(original_index)
        current_tokens += block_tokens

    if current_blocks:
        chunks.append(
            create_chunk(
                section,
                current_blocks,
                current_mapping[0],
                current_mapping[-1] + 1
            )
        )

    return chunks


def pack_sections(
    sections: list[Section],
    token_counter,
    target_tokens: int = 600,
    max_tokens: int = 800
):
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