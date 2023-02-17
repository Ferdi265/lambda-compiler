from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy

from .ast import *
from .resolve import Local, Global
from .continuations import *

@dataclass
class ImplementationLiteral(ValueLiteral):
    impl: Implementation

@dataclass
class Implementation(Statement):
    name: str
    lambda_id: int
    continuation_id: int
    arg_literal: Optional[ValueLiteral]
    ident_captures: Set[str]
    anonymous_captures: Set[int]

@dataclass
class ReturnImplementation(Implementation):
    value: ValueLiteral

@dataclass
class TailCallImplementation(Implementation):
    fn: ValueLiteral
    arg: ValueLiteral

@dataclass
class ContinueCallImplementation(Implementation):
    fn: ValueLiteral
    arg: ValueLiteral
    next: ValueLiteral

class FlattenImplsError(Exception):
    pass

@dataclass
class FlattenImplsContext:
    current_assignment: str = field(default_factory = str)
    current_lambda_id: int = field(default_factory = int)
    implementations: List[Implementation] = field(default_factory = list)

    def lambda_context(self, arg_name: Optional[str]) -> LambdaContext:
        id = self.current_lambda_id
        self.current_lambda_id += 1
        return LambdaContext(self, arg_name, id)

    def implementation_literal(self, lambda_id: int, continuation_id: int, arg_name: Optional[ValueLiteral], ident_captures: Set[str], anonymous_captures: Set[int]) -> ImplementationLiteral:
        return ImplementationLiteral(Implementation(
            self.current_assignment, lambda_id, continuation_id,
            arg_name, ident_captures, anonymous_captures
        ))

I = TypeVar("I", bound = Implementation)

@dataclass
class LambdaContext:
    ctx: FlattenImplsContext
    arg_name: Optional[str]
    lambda_id: int
    current_continuation_id: int = field(default_factory = int)

    def next_continuation_id(self) -> int:
        id = self.current_continuation_id
        self.current_continuation_id += 1
        return id

    def _impl_metadata(self) -> Tuple[str, int, int, Optional[ValueLiteral], Set[str], Set[int]]:
        continuation_id = self.next_continuation_id()

        arg_lit: Optional[ValueLiteral]
        if self.arg_name is not None:
            arg_lit = IdentLiteral(Local(self.arg_name))
            self.arg_name = None
        elif continuation_id == 0:
            arg_lit = None
        else:
            arg_lit = AnonymousLiteral(continuation_id - 1)

        return self.ctx.current_assignment, self.lambda_id, continuation_id, arg_lit, set(), set()

    def _append(self, impl: I) -> I:
        self.ctx.implementations.append(impl)
        return impl

    def append_return(self, value: ValueLiteral) -> ReturnImplementation:
        return self._append(ReturnImplementation(*self._impl_metadata(), value))

    def append_tail_call(self, fn: ValueLiteral, arg: ValueLiteral) -> TailCallImplementation:
        return self._append(TailCallImplementation(*self._impl_metadata(), fn, arg))

    def append_continue_call(self, fn: ValueLiteral, arg: ValueLiteral, next: ValueLiteral) -> ContinueCallImplementation:
        return self._append(ContinueCallImplementation(*self._impl_metadata(), fn, arg, next))

def flatten_implementations(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        ctx = FlattenImplsContext()

        for stmt in prog:
            visit_statement(stmt, ctx)

        return cast(List[Statement], ctx.implementations)

    def visit_statement(stmt: Statement, ctx: FlattenImplsContext):
        match stmt:
            case ContinuationAssignment() as ass:
                visit_assignment(ass, ctx)
            case _:
                raise FlattenImplsError(f"unexpected AST node encountered: {stmt}")

    def visit_assignment(ass: ContinuationAssignment, ctx: FlattenImplsContext):
        ctx.current_assignment = ass.name
        ctx.current_lambda_id = 0
        visit_continuation_chain(ass.value, ctx, None)

    def visit_continuation_chain(chain: ContinuationChain, ctx: FlattenImplsContext, arg_name: Optional[str]) -> int:
        lctx = ctx.lambda_context(arg_name)

        # check for single return
        if len(chain.continuations) == 0:
            last_ident_captures: Set[str] = set()
            match chain.result_literal:
                case LambdaLiteral(lamb):
                    last_ident_captures = lamb.captures

            value_lit = visit_literal(chain.result_literal, ctx)
            impl: Implementation = lctx.append_return(value_lit)
            impl.ident_captures = copy(last_ident_captures)

            if arg_name is not None:
                impl.ident_captures.remove(arg_name)

            return lctx.lambda_id

        # assert tail call optimization is valid
        if chain.result_literal != AnonymousLiteral(len(chain.continuations) - 1):
            raise FlattenImplsError(f"unexpected result literal {chain.result_literal} in {ctx.current_assignment} lambda {lctx.lambda_id}")

        # check if direct continuation optimization is valid
        direct_continuation_optimization = (chain.continuations[-1].arg == AnonymousLiteral(len(chain.continuations) - 2))

        for i, cont in enumerate(chain.continuations):
            fn_lit = visit_literal(cont.fn, ctx)
            arg_lit = visit_literal(cont.arg, ctx)

            if i + 1 < len(chain.continuations):
                next = chain.continuations[i + 1]

                if direct_continuation_optimization and i == len(chain.continuations) - 2:
                    next_lit = visit_literal(next.fn, ctx)
                else:
                    next_lit = ctx.implementation_literal(lctx.lambda_id, i + 1, AnonymousLiteral(i + 1), copy(next.ident_captures), copy(next.anonymous_captures))

                impl = lctx.append_continue_call(fn_lit, arg_lit, next_lit)
            else:
                impl = lctx.append_tail_call(fn_lit, arg_lit)

            impl.ident_captures = copy(cont.ident_captures)
            impl.anonymous_captures = copy(cont.anonymous_captures)

            if direct_continuation_optimization and i == len(chain.continuations) - 2:
                break

        return lctx.lambda_id

    def visit_literal(lit: ValueLiteral, ctx: FlattenImplsContext) -> ValueLiteral:
        match lit:
            case LambdaLiteral(lamb):
                lambda_id = visit_continuation_chain(lamb.body, ctx, lamb.name)
                return ctx.implementation_literal(lambda_id, 0, IdentLiteral(Local(lamb.name)), copy(lamb.captures), set())
            case other:
                return other

    return visit_program(prog)
