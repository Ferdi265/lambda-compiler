from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy

from .collect import *

class ResolveError(Exception):
    pass

def resolve(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement) -> Statement:
        match stmt:
            case PathAssignment() as ass:
                return visit_path_assignment(ass)

        return stmt

    def visit_path_assignment(ass: PathAssignment) -> Assignment:
        value = visit_expr(ass.value, CollectExprContext(True))

        return PathAssignment(ass.path, value, ass.is_public, ass.is_impure)

    def visit_expr(expr: Expr, ctx: CollectExprContext) -> Expr:
        match expr:
            case Paren(inner):
                return Paren(visit_expr(inner, ctx))
            case Call(fn, arg):
                return Call(visit_expr(fn, ctx), visit_expr(arg, ctx))
            case Lambda() as lamb:
                return visit_lambda(lamb, ctx)
            case Ident() as ident:
                return visit_ident(ident, ctx)
            case PathExpr() as path_expr:
                return visit_path_expr(path_expr, ctx)
            case unknown:
                raise ResolveError(f"unexpected AST node encountered: {unknown}")

    def visit_lambda(lamb: Lambda, ctx: CollectExprContext) -> Lambda:
        subctx = copy(ctx)
        subctx.locals.add(lamb.name)

        body = visit_expr(lamb.body, subctx)
        captures = ctx.locals & subctx.referenced
        captures.remove(lamb.name)

        ctx.referenced |= captures

        return Lambda(lamb.name, body, captures)

    def visit_ident(ident: Ident, ctx: CollectExprContext) -> Expr:
        if ident.name in ctx.locals:
            ctx.referenced.add(ident.name)
            return Local(ident.name)
        else:
            return ExternGlobal(ident.name)

    def visit_path_expr(path_expr: PathExpr, ctx: CollectExprContext) -> Expr:
        return PathGlobal(path_expr.path)

    return visit_program(prog)
