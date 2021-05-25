from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy

from .ast import *
from .resolve import Local, Global
from .continuations import *

@dataclass
class ImplementationLiteral(Literal):
    impl: Implementation

@dataclass
class Implementation(Statement):
    name: str
    lambda_id: int
    continuation_id: int
    arg_name: Optional[Literal]
    ident_captures: Set[str]
    anonymous_captures: Set[int]

@dataclass
class ReturnImplementation(Implementation):
    value: Literal

@dataclass
class TailCallImplementation(Implementation):
    fn: Literal
    arg: Literal

@dataclass
class ContinueCallImplementation(Implementation):
    fn: Literal
    arg: Literal
    next: Literal

class FlattenImplError(Exception):
    pass

@dataclass
class Context:
    current_assignment: str = field(default_factory = str)
    current_lambda_id: int = field(default_factory = int)
    implementations: List[Implementation] = field(default_factory = list)

    def next_lambda_id(self) -> int:
        id = self.current_lambda_id
        self.current_lambda_id += 1
        return id

    def append_return(self, lambda_id: int, continuation_id: int, arg_name: Optional[Literal], value: Literal) -> ReturnImplementation:
        impl = ReturnImplementation(
            self.current_assignment, lambda_id, continuation_id,
            arg_name, set(), set(),
            value
        )

        self.implementations.append(impl)
        return impl

    def append_tail_call(self, lambda_id: int, continuation_id: int, arg_name: Optional[Literal], fn: Literal, arg: Literal) -> TailCallImplementation:
        impl = TailCallImplementation(
            self.current_assignment, lambda_id, continuation_id,
            arg_name, set(), set(),
            fn, arg
        )

        self.implementations.append(impl)
        return impl

    def append_continue_call(self, lambda_id: int, continuation_id: int, arg_name: Optional[Literal], fn: Literal, arg: Literal, next: Literal) -> ContinueCallImplementation:
        impl = ContinueCallImplementation(
            self.current_assignment, lambda_id, continuation_id,
            arg_name, set(), set(),
            fn, arg, next
        )

        self.implementations.append(impl)
        return impl

def flatten_implementations(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        ctx = Context()

        for stmt in prog:
            visit_statement(stmt, ctx)

        return ctx.implementations

    def visit_statement(stmt: Statement, ctx: Context):
        match stmt:
            case ContinuationAssignment() as ass:
                visit_assignment(ass, ctx)

    def visit_assignment(ass: Assignment, ctx: Context):
        ctx.current_assignment = ass.name
        ctx.current_lambda_id = 0
        visit_continuation_chain(ass.value, ctx, None)

    def visit_continuation_chain(chain: ContinuationChain, ctx: Context, arg_name: Optional[str]) -> int:
        lambda_id = ctx.next_lambda_id()

        if arg_name is not None:
            arg_name_lit = IdentLiteral(Local(arg_name))
        else:
            arg_name_lit = None

        # check for single return
        if len(chain.continuations) == 0:
            last_ident_captures: Set[str] = set()
            match chain.result_literal:
                case LambdaLiteral(lamb):
                    last_ident_captures = lamb.captures

            value_lit = visit_literal(chain.result_literal, ctx)
            impl = ctx.append_return(lambda_id, 0, arg_name_lit, value_lit)
            impl.ident_captures = copy(last_ident_captures)

            if arg_name is not None:
                impl.ident_captures.remove(arg_name)

            return lambda_id

        # assert tail call optimization is valid
        if chain.result_literal != AnonymousLiteral(len(chain.continuations) - 1):
            raise FlattenImplError(f"unexpected result literal {chain.result_literal} in {ctx.current_assignment} lambda {lambda_id}")

        # check if direct continuation optimization is valid
        direct_continuation_optimization = (chain.continuations[-1].arg == AnonymousLiteral(len(chain.continuations) - 2))

        for i, cont in enumerate(chain.continuations):
            fn_lit = visit_literal(cont.fn, ctx)
            arg_lit = visit_literal(cont.arg, ctx)

            if i > 0:
                arg_name_lit = AnonymousLiteral(i - 1)

            if i + 1 < len(chain.continuations):
                next = chain.continuations[i + 1]

                if direct_continuation_optimization and i == len(chain.continuations) - 2:
                    next_lit = visit_literal(next.fn, ctx)
                else:
                    next_lit = ImplementationLiteral(Implementation(
                        ctx.current_assignment, lambda_id, i + 1,
                        AnonymousLiteral(i + 1), copy(next.ident_captures), copy(next.anonymous_captures)
                    ))

                impl = ctx.append_continue_call(lambda_id, i, arg_name_lit, fn_lit, arg_lit, next_lit)
            else:
                impl = ctx.append_tail_call(lambda_id, i, arg_name_lit, fn_lit, arg_lit)

            impl.ident_captures = copy(cont.ident_captures)
            impl.anonymous_captures = copy(cont.anonymous_captures)

            if direct_continuation_optimization and i == len(chain.continuations) - 2:
                break

        return lambda_id

    def visit_literal(lit: Literal, ctx: Context) -> Literal:
        match lit:
            case LambdaLiteral(lamb):
                lambda_id = visit_continuation_chain(lamb.body, ctx, lamb.name)
                return ImplementationLiteral(Implementation(
                    ctx.current_assignment, lambda_id, 0,
                    IdentLiteral(Local(lamb.name)), copy(lamb.captures), set()
                ))
            case other:
                return other

    return visit_program(prog)
