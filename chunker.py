import re
from copy import deepcopy

from parser.parsed_page import ParsedPage
from chunk_type import Chunk, MermaidDiagram

Heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")

def minify_table(lines: list[str]) -> str:
    return "".join(line.strip() for line in lines)

def chunker(data: dict[str, list[ParsedPage]]) -> list[Chunk]:
    sections = []
    for source, pages in data.items():
        heading_path = []
        current_chunk = None
        current_content = []
        for page in pages:
            lines = page.markdown.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                matched = Heading_pattern.match(line)
                if matched:
                    if current_chunk:
                        current_chunk.Content = "\n".join(current_content)
                        sections.append(current_chunk)
                    level = len(matched.group(1))
                    title = matched.group(2).strip()
                    while len(heading_path) >= level:
                        heading_path.pop()
                    heading_path.append(title)
                    current_chunk = Chunk(
                        Content="",
                        Source=source,
                        Title=title,
                        Heading_Path=deepcopy(heading_path),
                        page=page.page_number,
                        contains_image=False,
                        contains_table=False,
                        contains_formulas=False,
                    )
                    current_content = []
                    i += 1
                    continue
                if current_chunk is None:
                    i += 1
                    continue
                if line.startswith("'''mermaid"):
                    current_chunk.contains_image = True
                    previous = ""
                    for j in range(len(current_content) - 1, -1, -1):
                        if current_content[j].strip():
                            previous = current_content[j]
                            break
                    mermaid = [line]
                    i += 1
                    while i < len(lines):
                        mermaid.append(lines[i])
                        if lines[i].strip() == "'''":
                            break
                        i += 1
                    following = ""
                    k = i + 1
                    while k < len(lines):
                        next_line = lines[k].strip()
                        if not next_line:
                            k += 1
                            continue
                        if Heading_pattern.match(next_line):
                            break
                        if next_line.startswith("'''mermaid"):
                            break
                        if next_line.startswith("<table>"):
                            break
                        following = next_line
                        break
                    current_chunk.mermaid_diagrams.append(
                        MermaidDiagram(
                            previous=previous,
                            content="\n".join(mermaid),
                            following=following,
                        )
                    )
                    i += 1
                    continue
                if line.startswith("<table>"):
                    current_chunk.contains_table = True
                    table = [line]
                    i += 1
                    while i < len(lines):
                        table.append(lines[i])
                        if "</table>" in lines[i]:
                            break
                        i += 1
                    current_content.append(minify_table(table))
                    i += 1
                    continue
                if "$" in line:
                    current_chunk.contains_formulas = True
                current_content.append(line)
                i += 1
        if current_chunk:
            current_chunk.Content = "\n".join(current_content)
            sections.append(current_chunk)
    return sections