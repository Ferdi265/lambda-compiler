from collections import defaultdict
from dataclasses import dataclass, field
from ...ast.mlir_linked import *
from .dedup import DedupMLIRContext

class OptimizeNotYetSeenError(Exception):
    pass

class OptimizeMLIRError(Exception):
    pass

@dataclass
class OptimizeContext:
    dedup: DedupMLIRContext
    inst_id_table: Dict[Path, int] = field(default_factory = lambda: defaultdict(int))

    def next_inst_id(self, path: Path) -> int:
        id = self.inst_id_table[path]
        self.inst_id_table[path] += 1
        return id

    def bump_inst_id(self, inst: InstancePath):
        if self.inst_id_table[inst.path] <= inst.id:
            self.inst_id_table[inst.path] = inst.id + 1

    def instantiate(self, path: Path, impl: Implementation, impl_captures: List[int | LinkedInstance], captures: List[LinkedInstance]) -> LinkedInstance:
        captures = [captures[cap] if isinstance(cap, int) else cap for cap in impl_captures]

        inst = LinkedInstance(InstancePath(path, self.next_inst_id(path)), impl, captures)
        dedup_inst = self.dedup.dedup_new_inst(inst)
        return dedup_inst

    def evaluate_definition(self, defi: LinkedDefinition):
        if not defi.needs_init:
            return

        try:
            inst = self.evaluate_stack(defi.path, defi.inst.impl)
            defi.inst = inst
            defi.needs_init = False
        except OptimizeNotYetSeenError:
            pass

    def evaluate_stack(self, path: Path, impl: Implementation) -> LinkedInstance:
        stack: List[LinkedInstance] = []
        fn, arg = self.evaluate_impl(path, impl, [], stack)
        while fn is not None or len(stack) > 0:
            if fn is None:
                fn = stack.pop()
            fn, arg = self.evaluate_inst(path, fn, arg, stack)

        return arg

    def evaluate_inst(self, path: Path, inst: LinkedInstance, arg: LinkedInstance, stack: List[LinkedInstance]) -> Tuple[Optional[LinkedInstance], LinkedInstance]:
        return self.evaluate_impl(path, inst.impl, [arg] + inst.captures, stack)

    def evaluate_impl(self, path: Path, impl: Implementation, captures: List[LinkedInstance], stack: List[LinkedInstance]) -> Tuple[Optional[LinkedInstance], LinkedInstance]:
        match impl:
            case ReturnImplementation() as impl:
                return None, self.evaluate_literal(path, impl.value, captures)
            case TailCallImplementation() as impl:
                fn = self.evaluate_literal(path, impl.fn, captures)
                arg = self.evaluate_literal(path, impl.arg, captures)
                return fn, arg
            case ContinueCallImplementation() as impl:
                fn = self.evaluate_literal(path, impl.fn, captures)
                arg = self.evaluate_literal(path, impl.arg, captures)
                next = self.evaluate_literal(path, impl.next, captures)
                stack.append(next)
                return fn, arg
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {impl}")

    def evaluate_literal(self, path: Path, lit: ValueLiteral, captures: List[LinkedInstance]) -> LinkedInstance:
        match lit:
            case CaptureLiteral(id):
                return captures[id]
            case ExternLiteral(name):
                raise OptimizeNotYetSeenError()
            case LinkedDefinitionLiteral(defi):
                return defi.inst
            case LinkedInstanceLiteral(inst):
                return inst
            case LinkedImplementationLiteral(impl, impl_captures):
                return self.instantiate(path, impl, impl_captures, captures)
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {lit}")

def optimize_mlir(prog: List[Statement], opt_deps: Optional[List[Statement]] = None) -> List[Statement]:
    deps = opt_deps or []

    def visit_program(prog: List[Statement]) -> List[Statement]:
        dedup = DedupMLIRContext.build(deps + prog)
        ctx = OptimizeContext(dedup)

        for stmt in deps + prog:
            visit_statement_find_impls(stmt, ctx)

        for stmt in prog:
            visit_statement_instantiate(stmt, ctx)

        ctx.dedup.deduplicate(ctx.dedup.collect())
        return ctx.dedup.tree_shake(deps)

    def visit_statement_find_impls(stmt: Statement, ctx: OptimizeContext):
        match stmt:
            case ExternCrate() | Extern() | LinkedDefinition() | Implementation():
                pass
            case LinkedInstance() as inst:
                ctx.bump_inst_id(inst.path)
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_statement_instantiate(stmt: Statement, ctx: OptimizeContext):
        match stmt:
            case ExternCrate() | Extern() | LinkedInstance():
                pass
            case LinkedDefinition() as defi:
                ctx.evaluate_definition(defi)
            case Implementation() as impl:
                visit_implementation_instantiate(impl, ctx)
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_implementation_instantiate(impl: Implementation, ctx: OptimizeContext):
        match impl:
            case ReturnImplementation() as impl:
                impl.value = visit_literal(impl.path.path, impl.value, ctx)
            case TailCallImplementation() as impl:
                impl.fn = visit_literal(impl.path.path, impl.fn, ctx)
                impl.arg = visit_literal(impl.path.path, impl.arg, ctx)
            case ContinueCallImplementation() as impl:
                impl.fn = visit_literal(impl.path.path, impl.fn, ctx)
                impl.arg = visit_literal(impl.path.path, impl.arg, ctx)
                impl.next = visit_literal(impl.path.path, impl.next, ctx)
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {impl}")

        if impl.captures == 0:
            ctx.instantiate(impl.path.path, impl, [], [])

    def visit_literal(path: Path, lit: ValueLiteral, ctx: OptimizeContext) -> ValueLiteral:
        match lit:
            case LinkedDefinitionLiteral(defi):
                if not defi.needs_init:
                    return LinkedInstanceLiteral(defi.inst)
            case LinkedImplementationLiteral(impl, captures):
                if all(isinstance(cap, LinkedInstance) for cap in captures):
                    return LinkedInstanceLiteral(ctx.instantiate(path, impl, captures, []))

        return lit

    return visit_program(prog)
