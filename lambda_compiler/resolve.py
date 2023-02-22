from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy

from .ast import *

@dataclass
class Local(Ident):
    pass

@dataclass
class ExternGlobal(Ident):
    pass

@dataclass
class PathGlobal(PathExpr):
    pass

class ResolveError(Exception):
    pass

@dataclass
class Context:
    locals: OrderedSet[str] = field(default_factory = OrderedSet)
    globals: OrderedSet[Path] = field(default_factory = OrderedSet)
    externs: OrderedSet[str] = field(default_factory = OrderedSet)
    extern_crates: OrderedSet[str] = field(default_factory = OrderedSet)
    referenced: OrderedSet[str] = field(default_factory = OrderedSet)

    def __copy__(self) -> Context:
        return Context(copy(self.locals), copy(self.globals), copy(self.externs), copy(self.extern_crates), OrderedSet())

def resolve(prog: List[Statement], crate: str, externs: Optional[OrderedSet[str]] = None) -> List[Statement]:
    """resolve idents into locals and globals and populate lambda captures"""

    def visit_program(prog: List[Statement], ctx: Context) -> List[Statement]:
        statements = []
        for stmt in prog:
            new_stmt = visit_statement(stmt, ctx)
            if new_stmt is not None:
                statements.append(new_stmt)

        return statements

    def visit_statement(stmt: Statement, ctx: Context) -> Optional[Statement]:
        match stmt:
            case ExternCrate() as ext_crate:
                return visit_extern_crate(ext_crate, ctx)
            case Extern() as ext:
                return visit_extern(ext, ctx)
            case NameAssignment() as ass:
                return visit_name_assignment(ass, ctx)
            case PathAssignment() as ass:
                return visit_path_assignment(ass, ctx)
            case unknown:
                raise ResolveError(f"unexpected AST node encountered: {unknown}")

    def visit_extern_crate(ext_crate: ExternCrate, ctx: Context):
        if ext_crate.name in ctx.extern_crates:
            raise ResolveError(f"Redefinition of extern crate '{ext_crate.name}'")

        ctx.extern_crates.add(ext_crate.name)

    def visit_extern(ext: Extern, ctx: Context):
        if ext.name in ctx.externs:
            raise ResolveError(f"Redefinition of extern '{ext.name}'")

        ctx.externs.add(ext.name)

    def visit_name_assignment(ass: NameAssignment, ctx: Context) -> Assignment:
        if ass.name in ctx.externs:
            raise ResolveError(f"Redefinition of extern '{ass.name}'")

        path = Path(()) / crate / ass.name
        if path in ctx.globals:
            raise ResolveError(f"Redefinition of crate global '{ass.name}'")

        value = visit_expr(ass.value, copy(ctx))

        ctx.globals.add(path)
        return PathAssignment(path, value)

    def visit_path_assignment(ass: PathAssignment, ctx: Context) -> Assignment:
        if ass.path in ctx.globals:
            raise ResolveError(f"Redefinition of global '{ass.path}'")

        if ass.path.components[0] in ctx.extern_crates:
            raise ResolveError(f"Definition of extern crate global '{ass.path}'")

        value = visit_expr(ass.value, copy(ctx))

        ctx.globals.add(ass.path)
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
            case PathExpr() as path_expr:
                return visit_path_expr(path_expr, ctx)
            case unknown:
                raise ResolveError(f"unexpected AST node encountered: {unknown}")

    def visit_lambda(lamb: Lambda, ctx: Context) -> Lambda:
        subctx = copy(ctx)
        subctx.locals.add(lamb.name)

        body = visit_expr(lamb.body, subctx)
        captures = ctx.locals & subctx.referenced
        captures.remove(lamb.name)

        ctx.referenced |= captures

        return Lambda(lamb.name, body, captures)

    def visit_ident(ident: Ident, ctx: Context) -> Expr:
        ctx.referenced.add(ident.name)

        if ident.name in ctx.locals:
            return Local(ident.name)
        elif ident.name in ctx.externs:
            return ExternGlobal(ident.name)
        elif Path(()) / crate / ident.name in ctx.globals:
            return PathGlobal(Path(()) / crate / ident.name)
        else:
            raise ResolveError(f"'{ident.name}' is undefined")

    def visit_path_expr(path_expr: PathExpr, ctx: Context) -> Expr:
        path_crate_name = path_expr.path.components[0]

        if path_crate_name == crate:
            if path_expr.path in ctx.globals:
                return PathGlobal(path_expr.path)
            else:
                raise ResolveError(f"'{path_expr.path}' is undefined")
        else:
            if path_crate_name in ctx.extern_crates:
                return PathGlobal(path_expr.path)
            else:
                raise ResolveError(f"'{path_expr.path}' is from an undeclared extern crate")

    if externs is None:
        externs = OrderedSet()

    return visit_program(prog, Context(externs))
