from __future__ import annotations
from .path import *

@dataclass
class Statement:
    pass

@dataclass
class ExternCrate(Statement):
    name: str

@dataclass
class Extern(Statement):
    name: str

@dataclass
class Assignment(Statement):
    path: Path
    value: Expr
    is_public: bool
    is_impure: bool

@dataclass
class Alias(Statement):
    path: Path
    target: Path
    is_public: bool

@dataclass
class Expr:
    pass

@dataclass
class Ellipsis(Expr):
    pass

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

@dataclass
class Ident(Expr):
    name: str

@dataclass
class Absolute(Expr):
    path: Path
