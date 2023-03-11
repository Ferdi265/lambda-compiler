from .lang import *
from . import hlir

@dataclass
class LinkedExternCrate(Statement):
    name: str

    dir: str
    src: str
    owns_dir: bool

    prog: List[Statement] | List[hlir.Statement]

@dataclass
class LinkedMod(Statement):
    name: str
    is_public: bool

    dir: str
    src: str
    owns_dir: bool

    prog: List[Statement]
