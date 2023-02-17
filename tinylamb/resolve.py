from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy

from .ast import *

@dataclass
class Local(Ident):
    pass

@dataclass
class Global(Ident):
    pass

class ResolveError(Exception):
    pass

@dataclass
class Context:
    globals: Set[str] = field(default_factory = set)
    locals: Set[str] = field(default_factory = set)
    referenced: Set[str] = field(default_factory = set)

    def __copy__(self) -> Context:
        return Context(copy(self.globals), copy(self.locals))

    def __contains__(self, arg: str) -> bool:
        return arg in self.locals or arg in self.globals

def resolve(prog: List[Statement], globals: Set[str]) -> List[Statement]:
    """resolve idents into locals and globals and populate lambda captures"""

    def visit_program(prog: List[Statement], ctx: Context) -> List[Statement]:
        return [visit_statement(stmt, ctx) for stmt in prog]

    def visit_statement(stmt: Statement, ctx: Context) -> Statement:
        match stmt:
            case Assignment() as ass:
                return visit_assignment(ass, ctx)
            case unknown:
                raise ResolveError(f"unexpected AST node encountered: {unknown}")

    def visit_assignment(ass: Assignment, ctx: Context) -> Assignment:
        if ass.name in ctx.globals:
            raise ResolveError(f"Redefinition of '{ass.name}'")

        value = visit_expr(ass.value, copy(ctx))

        ctx.globals.add(ass.name)
        return Assignment(ass.name, value)

    def visit_expr(expr: Expr, ctx: Context) -> Expr:
        match expr:
            case Paren(inner):
                return Paren(visit_expr(inner, ctx))
            case Call(fn, arg):
                return Call(visit_expr(fn, ctx), visit_expr(arg, ctx))
            case Lambda() as lamb:
                return visit_lambda(lamb, ctx)
            case Ident() as ident:
                return visit_ident(ident, ctx)
            case unknown:
                raise ResolveError(f"unexpected AST node encountered: {unknown}")

    def visit_lambda(lamb: Lambda, ctx: Context) -> Lambda:
        subctx = copy(ctx)
        subctx.locals.add(lamb.name)

        body = visit_expr(lamb.body, subctx)
        captures = ctx.locals & subctx.referenced

        return Lambda(lamb.name, body, captures)

    def visit_ident(ident: Ident, ctx: Context) -> Ident:
        ctx.referenced.add(ident.name)

        if ident.name in ctx.locals:
            return Local(ident.name)
        elif ident.name in ctx.globals:
            return Global(ident.name)
        else:
            raise ResolveError(f"'{ident.name}' is undefined")

    return visit_program(prog, Context(globals))
