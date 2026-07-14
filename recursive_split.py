import re

from datastructures import AtomicBlock, PackedPart

LIST_PATTERN = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")

def recursive_split(
    block: AtomicBlock,
    token_counter,
    max_tokens: int
) -> list[AtomicBlock]:
    
    if token_counter(block.content) <= max_tokens:
        return [block]
    for splitter in (split_paragraphs, split_lists,split_lines,split_words) :
        parts, separator = splitter(block.content)
        if len(parts) <= 1:
            continue
        return split_parts(
            block,
            parts,
            separator,
            token_counter,
            max_tokens
        )

    return split_midpoint(
        block,
        block.content.split(),
        " ",
        token_counter,
        max_tokens
    )

def split_parts(
    block: AtomicBlock,
    parts: list[str],
    separator: str,
    token_counter,
    max_tokens: int
) -> list[AtomicBlock]:

    packed = pack_parts(
        parts,
        separator,
        token_counter,
        max_tokens
    )
    result = []
    for part in packed:
        child = AtomicBlock(
            type=block.type,
            content=part.content,
            page=block.page
        )
        if part.tokens <= max_tokens:
            result.append(child)
        else:
            result.extend(
                split_midpoint(
                    child,
                    child.content.split(),
                    " ",
                    token_counter,
                    max_tokens
                )
            )

    return result

def pack_parts(
    parts: list[str],
    separator: str,
    token_counter,
    max_tokens: int
) -> list[PackedPart]:
    
    packed = []
    current = []
    current_tokens = 0
    for part in parts:
        part_tokens = token_counter(part)
        if current and current_tokens + part_tokens > max_tokens:
            packed.append(
                PackedPart(
                    content=separator.join(current),
                    tokens=current_tokens))
            current = [part]
            current_tokens = part_tokens
        else:
            current.append(part)
            current_tokens += part_tokens
    if current:
        packed.append(
            PackedPart(
                content=separator.join(current),
                tokens=current_tokens
            )
        )
    return packed


def split_paragraphs(text: str) -> tuple[list[str], str]:
    return (
        [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ],
        "\n\n"
    )

def split_lists(text: str) -> tuple[list[str], str]:
    lines = text.splitlines()
    parts = []
    current = []
    in_list = False
    found_list = False
    for line in lines:
        is_list = bool(LIST_PATTERN.match(line))
        if is_list:
            found_list = True
            if not in_list and current:
                parts.append("\n".join(current).strip())
                current = []
            current.append(line)
            in_list = True
            continue
        if in_list:
            parts.append("\n".join(current).strip())
            current = []
        current.append(line)
        in_list = False
    if current:
        parts.append("\n".join(current).strip())
    if not found_list:
        return [text], "\n"
    
    
    return (
        [part for part in parts if part],
        "\n\n"
    )

def split_lines(text: str) -> tuple[list[str], str]:
    return (
        [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ],
        "\n"
    )

def split_words(text: str) -> tuple[list[str], str]:
    return (
        text.split(),
        " "
    )
#Hello
def split_midpoint(
    block: AtomicBlock,
    parts: list[str],
    separator: str,
    token_counter,
    max_tokens: int
) -> list[AtomicBlock]:
    if len(parts) <= 1:
        return split_characters(
            block,
            token_counter,
            max_tokens
        )
    midpoint = len(parts) // 2
    result = []
    for split in ( parts[:midpoint],parts[midpoint:]):
        child = AtomicBlock(
            type=block.type,
            content=separator.join(split).strip(),
            page=block.page
        )
        if not child.content:
            continue
        if token_counter(child.content) <= max_tokens:
            result.append(child)
        else:
            result.extend(
                split_midpoint(
                    child,
                    child.content.split(),
                    " ",
                    token_counter,
                    max_tokens
                )
            )

    return result

def split_characters(
    block: AtomicBlock,
    token_counter,
    max_tokens: int
) -> list[AtomicBlock]:
#Proud of this oneee...(:-:)
    text = block.content
    if len(text) <= 1:
        return [block]
    midpoint = len(text) // 2
    result = []
    for split in (text[:midpoint], text[midpoint:]):
        child = AtomicBlock(
            type=block.type,
            content=split.strip(),
            page=block.page
        )
        if not child.content:
            continue
        if token_counter(child.content) <= max_tokens:
            result.append(child)
        else:
            result.extend(
                split_characters(
                    child,
                    token_counter,
                    max_tokens
                )
            )

    return result