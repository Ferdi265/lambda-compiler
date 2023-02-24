from __future__ import annotations
from typing import *
from dataclasses import dataclass, field

from .ast import *

@dataclass
class CallStart(Expr):
    fn: Expr
    arg: Expr
    next: Optional[CallChain] = field(default_factory = lambda: None)

@dataclass
class CallChain(Expr):
    arg: Expr
    next: Optional[CallChain] = field(default_factory = lambda: None)

class RechainError(Exception):
    pass

def rechain(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement) -> Statement:
        match stmt:
            case PathAssignment(path, value, is_public, is_impure):
                return PathAssignment(path, visit_chain(value), is_public, is_impure)
            case _:
                raise RechainError(f"unexpected AST node encountered: {stmt}")

    def visit_expr(expr: Expr) -> Expr:
        match expr:
            case Paren(inner):
                return visit_chain(inner)
            case Call() as call:
                raise RechainError(f"unexpected Call encountered outside of visit_chain: {call}")
            case Lambda(name, body, captures):
                return Lambda(name, visit_chain(body), captures)
            case Ident() as ident:
                return ident
            case PathExpr() as path_expr:
                return path_expr
            case _:
                raise RechainError(f"unexpected AST node encountered: {expr}")

    def visit_chain(expr: Expr) -> Expr:
        chain = build_chain(expr)
        return unravel_chain(chain)

    def build_chain(expr: Expr) -> List[Expr]:
        chain = []
        while isinstance(expr, Call):
            chain.append(visit_expr(expr.arg))
            expr = expr.fn

        chain.append(visit_expr(expr))

        return chain

    def unravel_chain(chain: List[Expr]) -> Expr:
        if len(chain) == 0:
            raise RechainError("unexpected empty chain")
        if len(chain) == 1:
            return chain.pop()

        first = CallStart(chain.pop(), chain.pop())
        prev: Union[CallStart, CallChain] = first
        while len(chain) > 0:
            cur = CallChain(chain.pop())
            prev.next = cur
            prev = cur

        return first

    return visit_program(prog)
