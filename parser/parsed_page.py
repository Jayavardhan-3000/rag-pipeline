from dataclasses import dataclass

@dataclass
class ParsedPage:
    page_number: int
    markdown: str