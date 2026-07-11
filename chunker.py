import hashlib
import re
from copy import deepcopy

from chunk_type import AtomicBlock, MermaidDiagram, Section
from parser.enums import BlockType
from parser.parsed_page import ParsedPage

Heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")

def minify_table(lines: list[str]) -> str:
    return "".join(line.strip() for line in lines)

def flush_paragraph(paragraph: list[str], blocks: list[AtomicBlock], page: int):
    if not paragraph:
        return
    blocks.append(
        AtomicBlock(
            type=BlockType.TEXT,
            content="\n".join(paragraph).strip(),
            page=page
        )
    )
    paragraph.clear()

def generate_section_id(source: str, heading_path: list[str]) -> str:
    return hashlib.sha256(
        f"{source}|{'/'.join(heading_path)}".encode("utf-8")
    ).hexdigest()

def finalize_section(
    sections: list[Section],
    section: Section | None,
    blocks: list[AtomicBlock],
    mermaids: list[MermaidDiagram],
    contains_table: bool,
    contains_formulas: bool
):
    if section is None:
        return
    section.blocks = blocks
    section.mermaid_diagrams = mermaids
    section.contains_table = contains_table
    section.contains_formulas = contains_formulas
    sections.append(section)
def chunker(data: dict[str, list[ParsedPage]]) -> list[Section]:
    sections = []
    for source, pages in data.items():
        heading_path = []
        current_section = None
        current_blocks = []
        current_paragraph = []
        mermaid_diagrams = []
        contains_table = False
        contains_formulas = False
        for page in pages:
            lines = page.markdown.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                matched = Heading_pattern.match(line)
                if matched:
                    flush_paragraph(current_paragraph, current_blocks, page.page_number)
                    finalize_section(
                        sections,
                        current_section,
                        current_blocks,
                        mermaid_diagrams,
                        contains_table,
                        contains_formulas
                    )
                    level = len(matched.group(1))
                    title = matched.group(2).strip()
                    while len(heading_path) >= level:
                        heading_path.pop()
                    heading_path.append(title)
                    current_section = Section(
                        section_id=generate_section_id(source, heading_path),
                        source=source,
                        title=title,
                        heading_path=deepcopy(heading_path),
                        page=page.page_number,
                        contains_image=False,
                        contains_table=False,
                        contains_formulas=False,
                        blocks=[],
                        mermaid_diagrams=[]
                    )
                    current_blocks = []
                    current_paragraph = []
                    mermaid_diagrams = []
                    contains_table = False
                    contains_formulas = False
                    i += 1
                    continue
                if current_section is None:
                    i += 1
                    continue
                if not line.strip():
                    flush_paragraph(current_paragraph, current_blocks, page.page_number)
                    i += 1
                    continue
                if line.startswith("'''mermaid"):
                    flush_paragraph(current_paragraph, current_blocks, page.page_number)
                    current_section.contains_image = True
                    previous = ""
                    if current_blocks and current_blocks[-1].type == BlockType.TEXT:
                        previous = current_blocks[-1].content
                    mermaid = [line]
                    i += 1
                    while i < len(lines):
                        mermaid.append(lines[i])
                        if lines[i].strip() == "'''":
                            break
                        i += 1
                    following = []
                    k = i + 1
                    while k < len(lines):
                        next_line = lines[k]
                        if not next_line.strip():
                            if following:
                                break
                            k += 1
                            continue
                        if (
                            Heading_pattern.match(next_line)
                            or next_line.startswith("'''mermaid")
                            or next_line.startswith("<table>")
                        ):
                            break
                        following.append(next_line)
                        k += 1
                    mermaid_diagrams.append(
                        MermaidDiagram(
                            previous=previous,
                            previous_embedding=None,
                            content="\n".join(mermaid),
                            following="\n".join(following),
                            following_embedding=None
                        )
                    )
                    i += 1
                    continue
                if line.startswith("<table>"):
                    flush_paragraph(current_paragraph, current_blocks, page.page_number)
                    contains_table = True
                    table = [line]
                    i += 1
                    while i < len(lines):
                        table.append(lines[i])
                        if "</table>" in lines[i]:
                            break
                        i += 1
                    current_blocks.append(
                        AtomicBlock(
                            type=BlockType.TABLE,
                            content=minify_table(table),
                            page=page.page_number
                        )
                    )
                    i += 1
                    continue
                if "$" in line:
                    contains_formulas = True
                current_paragraph.append(line)
                i += 1
        flush_paragraph(current_paragraph, current_blocks, page.page_number)
        finalize_section(
            sections,
            current_section,
            current_blocks,
            mermaid_diagrams,
            contains_table,
            contains_formulas
        )

    return sections