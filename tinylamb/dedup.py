from __future__ import annotations
from typing import *

from .renumber import *

class DedupNotYetSeenError(Exception):
    pass

class DedupImplementationsError(Exception):
    pass

@dataclass
class DedupImplementationsContext:
    implementations: List[Implementation] = field(default_factory = list)

    impl_hash: Dict[Tuple[str, int, int], tuple] = field(default_factory = dict)
    impl_dedup: Dict[tuple, Implementation] = field(default_factory = dict)

    def impl_hash_key(self, impl: Implementation) -> Tuple[str, int, int]:
        return (impl.name, impl.lambda_id, impl.continuation_id)

    def hash_literal(self, lit: ValueLiteral) -> tuple:
        match lit:
            case IdentLiteral(Global(ident)):
                return ("global", ident)
            case AnonymousLiteral(id):
                return ("anonymous", id)
            case ImplementationLiteral(impl):
                impl_hash_key = self.impl_hash_key(impl)
                if impl_hash_key not in self.impl_hash:
                    raise DedupNotYetSeenError()

                hash_value = self.impl_hash[impl_hash_key]
                lit.impl = self.impl_dedup[hash_value]

                return ("impl", hash_value, tuple(impl.anonymous_captures))
            case _:
                raise DedupImplementationsError(f"unexpected AST node encountered: {lit}")

    def hash_impl(self, impl: Implementation) -> Optional[tuple]:
        try:
            match impl:
                case ReturnImplementation() as impl:
                    return ("ret", self.hash_literal(impl.value))
                case TailCallImplementation() as impl:
                    return ("tail", self.hash_literal(impl.fn), self.hash_literal(impl.arg))
                case ContinueCallImplementation() as impl:
                    return ("cont", self.hash_literal(impl.fn), self.hash_literal(impl.arg), self.hash_literal(impl.next))
                case _:
                    raise DedupImplementationsError(f"unexpected AST node encountered: {impl}")
        except DedupNotYetSeenError:
            return None

    def deduplicate(self):
        print("before:", len(self.implementations))

        queue = self.implementations
        self.implementations = []
        while len(queue) > 0:
            next_queue = []
            for impl in queue:
                hash_value = self.hash_impl(impl)
                if hash_value is None:
                    next_queue.append(impl)
                    continue

                self.impl_hash[self.impl_hash_key(impl)] = hash_value
                if hash_value not in self.impl_dedup:
                    self.impl_dedup[hash_value] = impl
                    self.implementations.append(impl)

            queue = next_queue

        print("after:", len(self.implementations))

def dedup_implementations(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        ctx = DedupImplementationsContext()

        for stmt in prog:
            visit_statement(stmt, ctx)

        ctx.deduplicate()

        return cast(List[Statement], ctx.implementations)

    def visit_statement(stmt: Statement, ctx: DedupImplementationsContext):
        match stmt:
            case Implementation() as impl:
                visit_implementation(impl, ctx)
            case _:
                raise DedupImplementationsError(f"unexpected AST node encountered: {stmt}")

    def visit_implementation(impl: Implementation, ctx: DedupImplementationsContext):
        ctx.implementations.append(impl)

    return visit_program(prog)
