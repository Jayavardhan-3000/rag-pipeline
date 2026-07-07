from enum import Enum

class BlockType(Enum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    CODE = "code"
    EQUATION = "equation"