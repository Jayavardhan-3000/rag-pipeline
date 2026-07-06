from dataclasses import dataclass

@dataclass
class Chunk: #tells editor what it is expecting and also it gives warning, if gave wrong data type to an index or auto converts it
    Content : str
    Source : str
    Title : str
    Heading_Path : list[str]
    page: int
    contains_image : bool
    contains_table : bool
    contains_formulas : bool