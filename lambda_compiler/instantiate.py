from __future__ import annotations
from typing import *
from dataclasses import dataclass, field

from .dedup import *

class InstantiateNotYetSeenError(Exception):
    pass

class InstantiateError(Exception):
    pass

@dataclass
class InstantiateContext:
    dedup: DedupImplementationsContext

    impl_table: Dict[Tuple[Path, int, int], Implementation] = field(default_factory = dict)
    inst_table: Dict[Tuple[Path, int], Instance] = field(default_factory = dict)
    def_table: Dict[Path, InstanceDefinition] = field(default_factory = dict)

    impl_inst_table: Dict[Tuple[Path, int, int], Instance] = field(default_factory = dict)
    inst_id_table: Dict[Path, int] = field(default_factory = dict)

    instances: List[Instance] = field(default_factory = list)
    definitions: List[InstanceDefinition] = field(default_factory = list)

    def resolve_impl(self, impl: Implementation) -> Implementation:
        if (impl.path, impl.lambda_id, impl.continuation_id) not in self.impl_table:
            raise InstantiateNotYetSeenError()
        return self.impl_table[(impl.path, impl.lambda_id, impl.continuation_id)]

    def resolve_impl_inst(self, impl: Implementation) -> Instance:
        if (impl.path, impl.lambda_id, impl.continuation_id) not in self.impl_inst_table:
            raise InstantiateNotYetSeenError()
        return self.impl_inst_table[(impl.path, impl.lambda_id, impl.continuation_id)]

    def resolve_inst(self, inst: Instance) -> Instance:
        if (inst.path, inst.inst_id) not in self.inst_table:
            raise InstantiateNotYetSeenError()
        return self.inst_table[(inst.path, inst.inst_id)]

    def resolve_path_global(self, path: Path) -> Instance:
        if path not in self.def_table:
            raise InstantiateNotYetSeenError()
        return self.def_table[path].inst

    def next_inst_id(self, path: Path) -> int:
        if path not in self.inst_id_table:
            self.inst_id_table[path] = 0

        id = self.inst_id_table[path]
        self.inst_id_table[path] += 1
        return id

    def instantiate(self, path: Path, impl: Implementation, captures: List[Instance]) -> Instance:
        captures = [captures[i] for i in impl.anonymous_captures]

        inst: Instance = Instance(path, self.next_inst_id(path), impl, captures)
        self.inst_table[(inst.path, inst.inst_id)] = inst
        self.impl_inst_table[(impl.path, impl.lambda_id, impl.continuation_id)] = inst

        dedup_inst = self.dedup.dedup_new_inst(inst)
        if dedup_inst is inst:
            self.instances.append(inst)

        return dedup_inst

    def evaluate_definition(self, impl: Implementation):
        assert len(impl.anonymous_captures) == 0

        try:
            inst = self.evaluate_stack(impl)
            needs_init = False
        except InstantiateNotYetSeenError:
            inst = self.resolve_impl_inst(impl)
            needs_init = True

        inst_def = InstanceDefinition(impl.path, inst, needs_init, impl.is_public)
        self.definitions.append(inst_def)
        self.def_table[impl.path] = inst_def
        self.dedup.insert_inst_def(inst_def)

    def evaluate_stack(self, impl: Implementation) -> Instance:
        path = impl.path

        stack: List[Instance] = []
        fn, arg = self.evaluate_impl(path, impl, [], stack)
        while fn is not None or len(stack) > 0:
            if fn is None:
                fn = stack.pop()
            fn, arg = self.evaluate_inst(path, fn, arg, stack)

        return arg

    def evaluate_inst(self, path: Path, inst: Instance, arg: Instance, stack: List[Instance]) -> Tuple[Optional[Instance], Instance]:
        return self.evaluate_impl(path, inst.impl, [arg] + inst.captures, stack)

    def evaluate_impl(self, path: Path, impl: Implementation, captures: List[Instance], stack: List[Instance]) -> Tuple[Optional[Instance], Instance]:
        impl = self.resolve_impl(impl)
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
                raise InstantiateError(f"unexpected AST node encountered: {impl}")

    def evaluate_literal(self, path: Path, lit: ValueLiteral, captures: List[Instance]) -> Instance:
        match lit:
            case PathLiteral(PathGlobal(path)):
                return self.resolve_path_global(path)
            case AnonymousLiteral(id):
                return captures[id]
            case InstanceLiteral(inst):
                return inst
            case ImplementationLiteral(impl):
                return self.instantiate(path, impl, captures)
            case _:
                raise InstantiateError(f"unexpected AST node encountered: {lit}")

def instantiate_implementations(prog: List[Statement], deps: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        dedup = build_dedup_context(deps + prog)
        ctx = InstantiateContext(dedup)

        for stmt in deps + prog:
            visit_statement_find_impls(stmt, ctx)

        for stmt in prog:
            visit_statement_instantiate(stmt, ctx)

        return tree_shake_dedup_context(ctx.dedup, deps)

    def visit_statement_find_impls(stmt: Statement, ctx: InstantiateContext):
        match stmt:
            case ExternCrate() | Instance():
                pass
            case InstanceDefinition() as inst:
                ctx.def_table[inst.path] = inst
            case Implementation() as impl:
                visit_implementation_find_impls(impl, ctx)
            case _:
                raise InstantiateError(f"unexpected AST node encountered: {stmt}")

    def visit_implementation_find_impls(impl: Implementation, ctx: InstantiateContext):
        ctx.impl_table[(impl.path, impl.lambda_id, impl.continuation_id)] = impl

    def visit_statement_instantiate(stmt: Statement, ctx: InstantiateContext):
        match stmt:
            case ExternCrate():
                pass
            case Implementation() as impl:
                visit_implementation_instantiate(impl, ctx)
            case _:
                raise InstantiateError(f"unexpected AST node encountered: {stmt}")

    def visit_implementation_instantiate(impl: Implementation, ctx: InstantiateContext):
        match impl:
            case ReturnImplementation() as impl:
                impl.value = visit_literal(impl.value, ctx)
            case TailCallImplementation() as impl:
                impl.fn = visit_literal(impl.fn, ctx)
                impl.arg = visit_literal(impl.arg, ctx)
            case ContinueCallImplementation() as impl:
                impl.fn = visit_literal(impl.fn, ctx)
                impl.arg = visit_literal(impl.arg, ctx)
                impl.next = visit_literal(impl.next, ctx)
            case _:
                raise InstantiateError(f"unexpected AST node encountered: {impl}")

        if len(impl.anonymous_captures) == 0:
            ctx.instantiate(impl.path, impl, [])

        if impl.lambda_id == 0 and impl.continuation_id == 0:
            ctx.evaluate_definition(impl)

    def visit_literal(lit: ValueLiteral, ctx: InstantiateContext) -> ValueLiteral:
        match lit:
            case PathLiteral(PathGlobal(path)):
                if path in ctx.def_table and not ctx.def_table[path].needs_init:
                    return InstanceLiteral(ctx.def_table[path].inst)
            case ImplementationLiteral(impl):
                impl = ctx.resolve_impl(impl)
                if len(impl.anonymous_captures) == 0:
                    return InstanceLiteral(ctx.instantiate(impl.path, impl, []))

        return lit

    return visit_program(prog)
