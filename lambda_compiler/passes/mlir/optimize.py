from collections import defaultdict
from dataclasses import dataclass, field
from ...ast.mlir_linked import *
from .dedup import DedupMLIRContext

class OptimizeCannotEvaluateError(Exception):
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
            inst = self.evaluate_impl_stack(defi.path, defi.inst.impl)
            defi.inst = inst
            defi.needs_init = False
        except OptimizeCannotEvaluateError:
            pass

    def evaluate_impl_stack(self, path: Path, impl: Implementation) -> LinkedInstance:
        stack: List[LinkedInstance] = []
        fn, arg = self.evaluate_impl(path, impl, [], stack)
        if fn is None:
            return arg
        else:
            return self.evaluate_inst_stack(path, fn, arg)

    def evaluate_inst_stack(self, path: Path, initial_fn: LinkedInstance, arg: LinkedInstance) -> LinkedInstance:
        stack: List[LinkedInstance] = []
        fn: Optional[LinkedInstance] = initial_fn
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
                raise OptimizeCannotEvaluateError()
            case LinkedDefinitionLiteral(defi):
                return defi.inst
            case LinkedInstanceLiteral(inst):
                return inst
            case LinkedImplementationLiteral(impl, impl_captures):
                return self.instantiate(path, impl, impl_captures, captures)
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {lit}")

    def can_optimize_impl(self, impl: Implementation) -> bool:
        match impl:
            case ReturnImplementation() as impl:
                return False
            case TailCallImplementation() as impl:
                return self.can_optimize_literal(impl.fn) and self.can_optimize_literal(impl.arg)
            case ContinueCallImplementation() as impl:
                # next does not need to be optimized
                return self.can_optimize_literal(impl.fn) and self.can_optimize_literal(impl.arg)
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {impl}")

    def can_optimize_literal(self, lit: ValueLiteral) -> bool:
        match lit:
            case CaptureLiteral() | ExternLiteral():
                return False
            case LinkedDefinitionLiteral() | LinkedInstanceLiteral():
                return True
            case LinkedImplementationLiteral(impl, impl_captures):
                for cap in impl_captures:
                    if isinstance(cap, int):
                        return False
                return True
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {lit}")

    def optimize_impl(self, impl: Implementation) -> Implementation:
        assert isinstance(impl, TailCallImplementation) or isinstance(impl, ContinueCallImplementation)
        path = impl.path.path
        fn = self.evaluate_literal(path, impl.fn, [])
        arg = self.evaluate_literal(path, impl.arg, [])

        res: Optional[LinkedInstance] = None
        try:
            res = self.evaluate_inst_stack(path, fn, arg)
        except OptimizeCannotEvaluateError:
            pass

        new_impl: Implementation
        captures: List[int | LinkedInstance]
        impl_metadata: Tuple[ImplementationPath, int] = (impl.path, impl.captures)
        if res is None:
            if isinstance(impl, TailCallImplementation):
                captures = [arg]
                captures += fn.captures
                new_impl = self.optimize_substitute_impl(impl, fn.impl, captures)
                self.dedup.replace_new_impl(new_impl, impl)
                return new_impl
            else:
                raise OptimizeCannotEvaluateError()
        elif isinstance(impl, TailCallImplementation):
            new_impl = ReturnImplementation(*impl_metadata, LinkedInstanceLiteral(res))
            self.dedup.replace_new_impl(new_impl, impl)
            return new_impl
        elif not isinstance(impl.next, LinkedImplementationLiteral):
            new_impl = TailCallImplementation(*impl_metadata, impl.next, LinkedInstanceLiteral(res))
            self.dedup.replace_new_impl(new_impl, impl)
            return new_impl
        else:
            captures = [res]
            captures += impl.next.captures
            new_impl = self.optimize_substitute_impl(impl, impl.next.impl, captures)
            self.dedup.replace_new_impl(new_impl, impl)
            return new_impl

    def optimize_substitute_impl(self, old_impl: Implementation, impl: Implementation, captures: List[int | LinkedInstance]) -> Implementation:
        impl_metadata: Tuple[ImplementationPath, int] = (old_impl.path, old_impl.captures)
        match impl:
            case ReturnImplementation():
                return ReturnImplementation(*impl_metadata,
                    self.optimize_literal(impl.value, captures)
                )
            case TailCallImplementation():
                return TailCallImplementation(*impl_metadata,
                    self.optimize_literal(impl.fn, captures),
                    self.optimize_literal(impl.arg, captures)
                )
            case ContinueCallImplementation():
                return ContinueCallImplementation(*impl_metadata,
                    self.optimize_literal(impl.fn, captures),
                    self.optimize_literal(impl.arg, captures),
                    self.optimize_literal(impl.next, captures),
                )
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {impl}")

    def optimize_literal(self, lit: ValueLiteral, captures: List[int | LinkedInstance]) -> ValueLiteral:
        match lit:
            case CaptureLiteral(id):
                match captures[id]:
                    case LinkedInstance() as inst:
                        return LinkedInstanceLiteral(inst)
                    case int() as i:
                        return CaptureLiteral(i)
                    case other:
                        raise OptimizeMLIRError(f"unexpected AST node encountered: {other}")
            case LinkedImplementationLiteral(impl, impl_captures):
                return LinkedImplementationLiteral(
                    impl,
                    [captures[cap] if isinstance(cap, int) else cap for cap in impl_captures]
                )
            case LinkedDefinitionLiteral() | LinkedInstanceLiteral():
                return lit
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {lit}")

def optimize_mlir(prog: List[Statement], opt_deps: Optional[List[Statement]] = None) -> List[Statement]:
    deps = opt_deps or []

    def visit_program(prog: List[Statement]) -> List[Statement]:
        dedup = DedupMLIRContext.build(deps + prog)
        ctx = OptimizeContext(dedup)

        for stmt in deps + prog:
            if isinstance(stmt, LinkedInstance):
                ctx.bump_inst_id(stmt.path)

        for stmt in prog:
            visit_statement(stmt, ctx)

        ctx.dedup.deduplicate(ctx.dedup.collect())
        return ctx.dedup.tree_shake(deps)

    def visit_statement(stmt: Statement, ctx: OptimizeContext):
        match stmt:
            case ExternCrate() | Extern() | LinkedInstance():
                pass
            case LinkedDefinition() as defi:
                ctx.evaluate_definition(defi)
            case Implementation() as impl:
                visit_implementation(impl, ctx)
            case _:
                raise OptimizeMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_implementation(impl: Implementation, ctx: OptimizeContext):
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

        impl, _ = ctx.dedup.dedup_impl(impl)

        try:
            while ctx.can_optimize_impl(impl):
                impl = ctx.optimize_impl(impl)
        except OptimizeCannotEvaluateError:
            # evaluation ran into an extern
            pass

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
