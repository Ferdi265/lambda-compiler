from .lang import *
from . import hlir_linked as hlir

@dataclass
class SourceFile:
    name: str

    dir: str
    src: str
    owns_dir: bool

    prog: List[Statement]

@dataclass
class LinkedMod(Statement):
    name: str
    is_public: bool

    file: SourceFile

@dataclass
class LinkedExternCrate(Statement):
    name: str

    file: SourceFile | hlir.SourceFile
