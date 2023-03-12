from __future__ import annotations
from typing import *
from .path import Path
from dataclasses import dataclass

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
class Mod(Statement):
    name: str
    is_public: bool

@dataclass
class Import(Statement):
    path: Path
    name: str
    is_public: bool

@dataclass
class ImportAll(Statement):
    path: Path
    is_public: bool

@dataclass
class Assignment(Statement):
    name: str
    value: Expr
    is_public: bool
    is_impure: bool

@dataclass
class Expr:
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
class Relative(Expr):
    path: Path

@dataclass
class Macro(Expr):
    pass

@dataclass
class String(Macro):
    content: str

@dataclass
class Number(Macro):
    value: int
