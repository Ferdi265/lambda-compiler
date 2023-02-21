from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from .orderedset import OrderedSet

@dataclass
class Statement:
    pass

@dataclass
class Expr:
    pass

@dataclass(frozen=True, init=False)
class Path:
    components: Sequence[str]

    def __init__(self, components: Sequence[str]):
        object.__setattr__(self, "components", tuple(components))

    def __str__(self) -> str:
        return "::".join(self.components)

    def __repr__(self) -> str:
        return str(self)

    def __lt__(self, other: Path) -> bool:
        return tuple(self.components) < tuple(other.components)

    def __truediv__(self, other: Union[Path, str]) -> Path:
        if isinstance(other, Path):
            return Path(tuple(self.components) + tuple(other.components))
        else:
            return Path(tuple(self.components) + (other,))

@dataclass
class ExternCrate(Statement):
    name: str

@dataclass
class Extern(Statement):
    name: str

@dataclass
class Assignment(Statement):
    pass

@dataclass
class NameAssignment(Assignment):
    name: str
    value: Expr

@dataclass
class PathAssignment(Assignment):
    path: Path
    value: Expr

@dataclass
class Import(Statement):
    path: Path
    name: Optional[str]

@dataclass
class Paren(Expr):
    inner: Expr

@dataclass
class Call(Expr):
    fn: Expr
    arg: Expr

@dataclass
class Lambda(Expr):
    name: str
    body: Expr
    captures: OrderedSet[str] = field(default_factory = OrderedSet)

@dataclass
class Ident(Expr):
    name: str

@dataclass
class PathExpr(Expr):
    path: Path

@dataclass
class String(Expr):
    content: str
