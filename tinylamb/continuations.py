from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy

from .ast import *
from .resolve import Local, Global
from .rechain import CallStart, CallChain

@dataclass
class Literal:
    pass

@dataclass
class IdentLiteral(Literal):
    ident: Ident

@dataclass
class AnonymousLiteral(Literal):
    id: int

@dataclass
class LambdaLiteral(Literal):
    lamb: ContinuationLambda

@dataclass
class Continuation:
    id: int
    fn: Literal
    arg: Literal
    ident_captures: Set[str] = field(default_factory = set)
    anonymous_captures: Set[int] = field(default_factory = set)

@dataclass
class ContinuationAssignment(Statement):
    name: str
    value: ContinuationChain

@dataclass
class ContinuationChain(Expr):
    continuations: List[Continuation]
    result_literal: Literal

@dataclass
class ContinuationLambda(Expr):
    name: str
    body: ContinuationChain
    captures: Set[str] = field(default_factory = set)

@dataclass
class Context:
    current_id: int = field(default_factory = int)
    continuations: List[Continuation] = field(default_factory = list)

    def append(self, fn: Literal, arg: Literal) -> Literal:
        id = self.current_id
        self.current_id += 1

        self.continuations.append(Continuation(id, fn, arg))
        return AnonymousLiteral(id)

def compute_continuations(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement) -> Statement:
        match stmt:
            case Assignment() as ass:
                return visit_assignment(ass)

    def visit_assignment(ass: Assignment) -> ContinuationAssignment:
        chain = make_continuation_chain(ass.value)
        visit_continuation_chain(chain, None)

        return ContinuationAssignment(ass.name, chain)

    def make_continuation_chain(expr: Expr) -> ContinuationChain:
        ctx = Context()
        lit = visit_expr(expr, ctx)
        return ContinuationChain(ctx.continuations, lit)

    def visit_expr(expr: Expr, ctx: Context) -> Literal:
        match expr:
            case CallStart() as call:
                return visit_call_start(call, ctx)
            case Lambda(name, body, captures):
                clamb = ContinuationLambda(name, make_continuation_chain(body), copy(captures))
                return LambdaLiteral(clamb)
            case Ident() as ident:
                return IdentLiteral(ident)

    def visit_call_start(call: CallStart, ctx: Context) -> Literal:
        lit = ctx.append(visit_expr(call.fn, ctx), visit_expr(call.arg, ctx))

        chain = call.next
        while chain is not None:
            lit = ctx.append(lit, visit_expr(chain.arg, ctx))
            chain = chain.next

        return lit

    def visit_continuation_chain(chain: ContinuationChain, arg: Optional[str]):
        next: Optional[Continuation] = None

        last_ident_captures: Set[str] = set()
        match chain.result_literal:
            case LambdaLiteral(lamb):
                visit_continuation_chain(lamb.body, lamb.name)
                last_ident_captures = lamb.captures

        for cur in reversed(chain.continuations):
            if next is None:
                cur.ident_captures |= last_ident_captures
            else:
                cur.ident_captures |= next.ident_captures
                cur.anonymous_captures |= next.anonymous_captures
                cur.anonymous_captures.remove(cur.id)

            visit_literal(cur.fn, cur)
            visit_literal(cur.arg, cur)

            if cur.id == 0:
                if arg is not None:
                    cur.ident_captures.remove(arg)
            else:
                cur.anonymous_captures.remove(cur.id - 1)

    def visit_literal(lit: Literal, cur: ContinuationChain):
        match lit:
            case AnonymousLiteral(id):
                cur.anonymous_captures.add(id)
            case IdentLiteral(Local(name)):
                cur.ident_captures.add(name)
            case LambdaLiteral(lamb):
                visit_continuation_chain(lamb.body, lamb.name)
                cur.ident_captures |= lamb.captures

    return visit_program(prog)
