from .hlir import *

@dataclass
class LinkedExternCrate(Statement):
    name: str

    dir: str
    src: str
    owns_dir: bool

    prog: List[Statement]
