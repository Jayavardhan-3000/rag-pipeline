import re
from copy import deepcopy
from parser.parsed_page import ParsedPage
from chunk_type import Chunk

"""
class Chunk: #tells editor what it is expecting and also it gives warning, if gave wrong data type to an index or auto converts it
    Content : str
    Source : str
    Title : str
    Heading_Path : list[str]
    page: int
    contains_image : bool
    contains_table : bool
    contains_formulas : bool

"""
Heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")
LINE_TAGS = {
    "<table>": "contains_table",
    "'''mermaid": "contains_image",
    "<sup>": "contains_superscript"
}
def chunker(data : dict[str, list[ParsedPage]]):
    sections : list[Chunk] = []
    for source, pages in data.items():
        heading_path = []
        current_chunk = None
        current_content = []
        for page in pages:
            for line in page.markdown.splitlines():
                matched = Heading_pattern.match(line)
                if matched:
                    if current_chunk is not None:
                        current_chunk.Content = "\n".join(current_content)
                        sections.append(current_chunk)
                    level = len(matched.group(1))
                    title = matched.group(2).strip()
                    while(len(heading_path) >= level):
                        heading_path.pop()
                    heading_path.append(title)
                    current_chunk = Chunk(
                        Content = "",
                        Source = source,
                        Title = title,
                        Heading_Path = deepcopy(heading_path),
                        page = page.page_number,
                        contains_image  = False,
                        contains_table  = False,
                        contains_formulas = False,
                        )
                    current_content = []
                    continue
                if current_chunk is None:
                    continue
                for tag, attribute in LINE_TAGS.items():
                    if line.startswith(tag):
                        setattr(current_chunk, attribute, True)
                        break
                if "$" in line:
                    current_chunk.contains_formulas = True
                current_content.append(line)
        if current_chunk:
            current_chunk.Content = "\n".join(current_content)
            sections.append(current_chunk)
    return sections