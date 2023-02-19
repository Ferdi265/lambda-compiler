from typing import *
from dataclasses import dataclass, field
from .orderedset import OrderedSet

@dataclass
class Statement:
    pass

@dataclass
class Expr:
    pass

@dataclass
class Assignment(Statement):
    name: str
    value: Expr

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
