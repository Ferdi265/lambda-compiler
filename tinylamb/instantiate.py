from __future__ import annotations
from typing import *
from dataclasses import dataclass, field

from .renumber import *

@dataclass
class Instance(Statement):
    name: str
    inst_id: int
    impl: Implementation
    captures: List[Instance]

@dataclass
class InstanceDefinition(Statement):
    name: str
    inst: Instance

@dataclass
class InstanceLiteral(ValueLiteral):
    inst: Instance

class InstantiateError(Exception):
    pass

@dataclass
class InstantiateContext:
    impl_table: Dict[Tuple[str, int, int], Implementation] = field(default_factory = dict)
    inst_table: Dict[Tuple[str, int], Instance] = field(default_factory = dict)
    def_table: Dict[str, InstanceDefinition] = field(default_factory = dict)

    impl_inst_table: Dict[Tuple[str, int, int], Instance] = field(default_factory = dict)
    inst_id_table: Dict[str, int] = field(default_factory = dict)

    instances: List[Instance] = field(default_factory = list)
    definitions: List[InstanceDefinition] = field(default_factory = list)

    def resolve_impl(self, impl: Implementation) -> Implementation:
        return self.impl_table[(impl.name, impl.lambda_id, impl.continuation_id)]

    def resolve_inst(self, inst: Instance) -> Instance:
        return self.inst_table[(inst.name, inst.inst_id)]

    def resolve_global(self, name: str) -> Instance:
        return self.def_table[name].inst

    def next_inst_id(self, name: str) -> int:
        if name not in self.inst_id_table:
            self.inst_id_table[name] = 0

        id = self.inst_id_table[name]
        self.inst_id_table[name] += 1
        return id

    def instantiate(self, impl: Implementation, captures: List[Instance]) -> Instance:
        captures = [captures[i] for i in impl.anonymous_captures]

        inst: Instance = Instance(impl.name, self.next_inst_id(impl.name), impl, captures)
        self.inst_table[(inst.name, inst.inst_id)] = inst
        self.impl_inst_table[(impl.name, impl.lambda_id, impl.continuation_id)] = inst
        self.instances.append(inst)
        return inst

    def evaluate_definition(self, impl: Implementation):
        assert len(impl.anonymous_captures) == 0

        inst = self.evaluate_impl(impl, [])
        inst_def = InstanceDefinition(impl.name, inst)
        self.definitions.append(inst_def)
        self.def_table[impl.name] = inst_def

    def evaluate_inst(self, inst: Instance, arg: Instance) -> Instance:
        return self.evaluate_impl(inst.impl, [arg] + inst.captures)

    def evaluate_impl(self, impl: Implementation, captures: List[Instance]) -> Instance:
        impl = self.resolve_impl(impl)
        match impl:
            case ReturnImplementation() as impl:
                return self.evaluate_literal(impl.value, captures)
            case TailCallImplementation() as impl:
                fn = self.evaluate_literal(impl.fn, captures)
                arg = self.evaluate_literal(impl.arg, captures)
                return self.evaluate_inst(fn, arg)
            case ContinueCallImplementation() as impl:
                fn = self.evaluate_literal(impl.fn, captures)
                arg = self.evaluate_literal(impl.arg, captures)
                next = self.evaluate_literal(impl.next, captures)
                ret = self.evaluate_inst(fn, arg)
                return self.evaluate_inst(next, ret)
            case _:
                raise InstantiateError(f"unexpected AST node encountered: {impl}")

    def evaluate_literal(self, lit: ValueLiteral, captures: List[Instance]) -> Instance:
        match lit:
            case IdentLiteral(Global(ident)):
                return self.resolve_global(ident)
            case AnonymousLiteral(id):
                return captures[id]
            case InstanceLiteral(inst):
                return inst
            case ImplementationLiteral(impl):
                return self.instantiate(impl, captures)
            case _:
                raise InstantiateError(f"unexpected AST node encountered: {lit}")

def instantiate_implementations(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        ctx = InstantiateContext()

        for stmt in prog:
            visit_statement_find_impls(stmt, ctx)

        for stmt in prog:
            visit_statement_instantiate(stmt, ctx)

        return prog + cast(List[Statement], ctx.instances) + cast(List[Statement], ctx.definitions)

    def visit_statement_find_impls(stmt: Statement, ctx: InstantiateContext):
        match stmt:
            case Implementation() as impl:
                visit_implementation_find_impls(impl, ctx)
            case _:
                raise InstantiateError(f"unexpected AST node encountered: {stmt}")

    def visit_implementation_find_impls(impl: Implementation, ctx: InstantiateContext):
        ctx.impl_table[(impl.name, impl.lambda_id, impl.continuation_id)] = impl

    def visit_statement_instantiate(stmt: Statement, ctx: InstantiateContext):
        match stmt:
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
            ctx.instantiate(impl, [])

        if impl.lambda_id == 0 and impl.continuation_id == 0:
            ctx.evaluate_definition(impl)

    def visit_literal(lit: ValueLiteral, ctx: InstantiateContext) -> ValueLiteral:
        match lit:
            case ImplementationLiteral(impl):
                impl = ctx.resolve_impl(impl)
                if len(impl.anonymous_captures) == 0:
                    return InstanceLiteral(ctx.instantiate(impl, []))

        return lit

    return visit_program(prog)