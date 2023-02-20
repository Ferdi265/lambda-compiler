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
    globals: OrderedSet[str] = field(default_factory = OrderedSet)
    locals: OrderedSet[str] = field(default_factory = OrderedSet)
    referenced: OrderedSet[str] = field(default_factory = OrderedSet)
    path_globals: OrderedSet[Path] = field(default_factory = OrderedSet)

    def __copy__(self) -> Context:
        return Context(copy(self.globals), copy(self.locals), OrderedSet(), copy(self.path_globals))

def resolve(prog: List[Statement], globals: Optional[OrderedSet[str]] = None, crate: Optional[Path] = None) -> List[Statement]:
    """resolve idents into locals and globals and populate lambda captures"""

    def visit_program(prog: List[Statement], ctx: Context) -> List[Statement]:
        return [visit_statement(stmt, ctx) for stmt in prog]

    def visit_statement(stmt: Statement, ctx: Context) -> Statement:
        match stmt:
            case NameAssignment() as ass:
                return visit_name_assignment(ass, ctx)
            case PathAssignment() as ass:
                return visit_path_assignment(ass, ctx)
            case unknown:
                raise ResolveError(f"unexpected AST node encountered: {unknown}")

    def visit_name_assignment(ass: NameAssignment, ctx: Context) -> Assignment:
        if ass.name in ctx.globals:
            raise ResolveError(f"Redefinition of '{ass.name}'")

        if crate is not None:
            path_name = crate / ass.name
            if path_name in ctx.path_globals:
                raise ResolveError(f"Redefinition of '{ass.name}' (previously defined as '{path_name}')")

        value = visit_expr(ass.value, copy(ctx))

        ctx.globals.add(ass.name)
        return NameAssignment(ass.name, value)

    def visit_path_assignment(ass: PathAssignment, ctx: Context) -> Assignment:
        if ass.path in ctx.path_globals:
            raise ResolveError(f"Redefinition of '{ass.path}'")

        if crate is not None:
            local_name = ass.path.components[-1]
            path_name = crate / local_name
            if path_name == ass.path and local_name in ctx.globals:
                raise ResolveError(f"Redefinition of '{ass.path}' (previously defined as '{local_name}')")

        value = visit_expr(ass.value, copy(ctx))

        ctx.path_globals.add(ass.path)
        return PathAssignment(ass.path, value)

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

        ctx.referenced |= captures

        return Lambda(lamb.name, body, captures)

    def visit_ident(ident: Ident, ctx: Context) -> Ident:
        ctx.referenced.add(ident.name)

        if ident.name in ctx.locals:
            return Local(ident.name)
        elif ident.name in ctx.globals:
            return Global(ident.name)
        else:
            raise ResolveError(f"'{ident.name}' is undefined")

    return visit_program(prog, Context(globals or OrderedSet()))
