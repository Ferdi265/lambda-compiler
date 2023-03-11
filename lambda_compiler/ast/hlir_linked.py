from .hlir import *

@dataclass
class SourceFile:
    name: str

    dir: str
    src: str
    owns_dir: bool

    prog: List[Statement]

@dataclass
class LinkedExternCrate(Statement):
    name: str

    file: SourceFile
