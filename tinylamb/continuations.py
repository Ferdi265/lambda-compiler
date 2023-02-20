from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy

from .ast import *
from .resolve import Local, ExternGlobal, PathGlobal
from .rechain import CallStart, CallChain

@dataclass
class ValueLiteral:
    pass

@dataclass
class IdentLiteral(ValueLiteral):
    ident: Ident

@dataclass
class PathLiteral(ValueLiteral):
    path: PathExpr

@dataclass
class AnonymousLiteral(ValueLiteral):
    id: int

@dataclass
class LambdaLiteral(ValueLiteral):
    lamb: CLambda

@dataclass
class Continuation:
    id: int
    fn: ValueLiteral
    arg: ValueLiteral
    ident_captures: OrderedSet[str] = field(default_factory = OrderedSet)
    anonymous_captures: OrderedSet[int] = field(default_factory = OrderedSet)

@dataclass
class ContinuationAssignment(Assignment):
    path: Path
    value: ContinuationChain

@dataclass
class ContinuationChain(Expr):
    continuations: List[Continuation]
    result_literal: ValueLiteral

@dataclass
class CLambda(Expr):
    name: str
    body: ContinuationChain
    captures: OrderedSet[str] = field(default_factory = OrderedSet)

class ComputeContinuationsError(Exception):
    pass

@dataclass
class ComputeContinuationsContext:
    current_id: int = field(default_factory = int)
    continuations: List[Continuation] = field(default_factory = list)

    def append(self, fn: ValueLiteral, arg: ValueLiteral) -> ValueLiteral:
        id = self.current_id
        self.current_id += 1

        self.continuations.append(Continuation(id, fn, arg))
        return AnonymousLiteral(id)

def compute_continuations(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement) -> Statement:
        match stmt:
            case PathAssignment() as ass:
                return visit_assignment(ass)
            case _:
                raise ComputeContinuationsError(f"unexpected AST node encountered: {stmt}")

    def visit_assignment(ass: PathAssignment) -> ContinuationAssignment:
        chain = make_continuation_chain(ass.value)
        visit_continuation_chain(chain, None)

        return ContinuationAssignment(ass.path, chain)

    def make_continuation_chain(expr: Expr) -> ContinuationChain:
        ctx = ComputeContinuationsContext()
        lit = visit_expr(expr, ctx)
        return ContinuationChain(ctx.continuations, lit)

    def visit_expr(expr: Expr, ctx: ComputeContinuationsContext) -> ValueLiteral:
        match expr:
            case CallStart() as call:
                return visit_call_start(call, ctx)
            case Lambda(name, body, captures):
                clamb = CLambda(name, make_continuation_chain(body), copy(captures))
                return LambdaLiteral(clamb)
            case Ident() as ident:
                return IdentLiteral(ident)
            case PathExpr() as path_expr:
                return PathLiteral(path_expr)
            case _:
                raise ComputeContinuationsError(f"unexpected AST node encountered: {expr}")

    def visit_call_start(call: CallStart, ctx: ComputeContinuationsContext) -> ValueLiteral:
        lit = ctx.append(visit_expr(call.fn, ctx), visit_expr(call.arg, ctx))

        chain = call.next
        while chain is not None:
            lit = ctx.append(lit, visit_expr(chain.arg, ctx))
            chain = chain.next

        return lit

    def visit_continuation_chain(chain: ContinuationChain, arg: Optional[str]):
        next: Optional[Continuation] = None

        last_ident_captures: OrderedSet[str] = OrderedSet()
        match chain.result_literal:
            case LambdaLiteral(lamb):
                visit_continuation_chain(lamb.body, lamb.name)

                if len(lamb.body.continuations) > 0:
                    lamb.captures = copy(lamb.body.continuations[0]).ident_captures
                    lamb.captures.remove(lamb.name)

                last_ident_captures = lamb.captures

        for cur in reversed(chain.continuations):
            if next is None:
                cur.ident_captures |= last_ident_captures
            else:
                cur.ident_captures |= next.ident_captures
                cur.anonymous_captures |= next.anonymous_captures

            visit_literal(cur.fn, cur)
            visit_literal(cur.arg, cur)

            if cur.id == 0:
                if arg is not None and arg in cur.ident_captures:
                    cur.ident_captures.remove(arg)
            else:
                if cur.id - 1 in cur.anonymous_captures:
                    cur.anonymous_captures.remove(cur.id - 1)

            next = cur

    def visit_literal(lit: ValueLiteral, cur: Continuation):
        match lit:
            case AnonymousLiteral(id):
                cur.anonymous_captures.add(id)
            case IdentLiteral(Local(name)):
                cur.ident_captures.add(name)
            case LambdaLiteral(lamb):
                visit_continuation_chain(lamb.body, lamb.name)
                cur.ident_captures |= lamb.captures

    return visit_program(prog)
