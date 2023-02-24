from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy

from .ast import *
from .flattenimpls import *

class RenumberCapturesError(Exception):
    pass

def renumber_captures(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement) -> Statement:
        match stmt:
            case Implementation() as impl:
                return visit_implementation(impl)
            case _:
                raise RenumberCapturesError(f"unexpected AST node encountered: {stmt}")

    def visit_implementation(impl: Implementation) -> Implementation:
        ident_capture_mapping: Dict[str, int] = {}
        anonymous_capture_mapping: Dict[int, int] = {}

        lit_counter = 0
        def map_literal(lit: Optional[ValueLiteral]) -> Optional[AnonymousLiteral]:
            nonlocal lit_counter

            new_id = lit_counter
            lit_counter += 1

            match lit:
                case None:
                    return None
                case IdentLiteral(Local(ident)):
                    ident_capture_mapping[ident] = new_id
                case AnonymousLiteral(id):
                    anonymous_capture_mapping[id] = new_id
                case _:
                    raise RenumberCapturesError(f"unexpected AST node encountered: {lit}")

            return AnonymousLiteral(new_id)

        def map_ident(ident: str) -> int:
            return cast(AnonymousLiteral, map_literal(IdentLiteral(Local(ident)))).id
        def map_anonymous(id: int) -> int:
            return cast(AnonymousLiteral, map_literal(AnonymousLiteral(id))).id

        def lookup_literal(lit: ValueLiteral) -> ValueLiteral:
            match lit:
                case IdentLiteral(Local(ident)):
                    return AnonymousLiteral(ident_capture_mapping[ident])
                case IdentLiteral(ExternGlobal(ident)):
                    return lit
                case PathLiteral(PathGlobal(path)):
                    return lit
                case AnonymousLiteral(id):
                    return AnonymousLiteral(anonymous_capture_mapping[id])
                case ImplementationLiteral(impl_ref):
                    new_impl_captures = []

                    for id in impl_ref.anonymous_captures:
                        new_impl_captures.append(lookup_anonymous(id))
                    for ident in impl_ref.ident_captures:
                        new_impl_captures.append(lookup_ident(ident))

                    # sanity checks
                    old_impl_captures = impl_ref.anonymous_captures + impl_ref.ident_captures
                    assert len(old_impl_captures) == len(new_impl_captures)

                    for a, b in zip(old_impl_captures, new_impl_captures):
                        if isinstance(a, str):
                            a_id = lookup_ident(a)
                        else:
                            a_id = lookup_anonymous(a)

                        assert a_id == b, f"mismatch: {a} ({a_id}) != {b}"

                    new_impl_ref = Implementation(
                        impl_ref.path,
                        impl_ref.lambda_id,
                        impl_ref.continuation_id,
                        None,
                        [],
                        new_impl_captures,
                        False
                    )
                    return ImplementationLiteral(new_impl_ref)
                case _:
                    raise RenumberCapturesError(f"unexpected AST node encountered: {lit}")

        def lookup_ident(ident: str) -> int:
            return cast(AnonymousLiteral, lookup_literal(IdentLiteral(Local(ident)))).id
        def lookup_anonymous(id: int) -> int:
            return cast(AnonymousLiteral, lookup_literal(AnonymousLiteral(id))).id

        if isinstance(impl.arg_literal, AnonymousLiteral):
            assert impl.arg_literal.id not in impl.anonymous_captures, "own argument in anonymous captures"

        new_impl = copy(impl)
        new_impl.arg_literal = map_literal(impl.arg_literal)
        new_impl.ident_captures = []
        new_impl.anonymous_captures = []

        for id in impl.anonymous_captures:
            new_impl.anonymous_captures.append(map_anonymous(id))
        for ident in impl.ident_captures:
            new_impl.anonymous_captures.append(map_ident(ident))

        match new_impl:
            case ReturnImplementation() as ret_impl:
                ret_impl.value = lookup_literal(ret_impl.value)
            case TailCallImplementation() as tail_impl:
                tail_impl.fn = lookup_literal(tail_impl.fn)
                tail_impl.arg = lookup_literal(tail_impl.arg)
            case ContinueCallImplementation() as cont_impl:
                cont_impl.fn = lookup_literal(cont_impl.fn)
                cont_impl.arg = lookup_literal(cont_impl.arg)
                cont_impl.next = lookup_literal(cont_impl.next)

        return new_impl

    return visit_program(prog)
