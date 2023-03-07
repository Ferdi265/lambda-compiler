from __future__ import annotations
from typing import *
from collections import defaultdict

from .renumber import *

@dataclass
class Instance(Statement):
    path: Path
    inst_id: int
    impl: Implementation
    captures: List[Instance]

@dataclass
class InstanceDefinition(Statement):
    path: Path
    inst: Instance
    needs_init: bool
    is_public: bool

@dataclass
class InstanceLiteral(ValueLiteral):
    inst: Instance

class DedupNotYetSeenError(Exception):
    pass

class DedupImplementationsError(Exception):
    pass

@dataclass
class DedupImplementationsContext:
    extern_crates: List[ExternCrate] = field(default_factory = list)
    implementations: List[Implementation] = field(default_factory = list)
    instances: List[Instance] = field(default_factory = list)
    definitions: List[InstanceDefinition] = field(default_factory = list)

    inst_hash: Dict[Tuple[Path, int], tuple] = field(default_factory = dict)
    impl_hash: Dict[Tuple[Path, int, int], tuple] = field(default_factory = dict)
    inst_dedup: Dict[tuple, Instance] = field(default_factory = dict)
    impl_dedup: Dict[tuple, Implementation] = field(default_factory = dict)

    def inst_hash_key(self, inst: Instance) -> Tuple[Path, int]:
        return (inst.path, inst.inst_id)

    def impl_hash_key(self, impl: Implementation) -> Tuple[Path, int, int]:
        return (impl.path, impl.lambda_id, impl.continuation_id)

    def dedup_inst(self, inst: Instance) -> Tuple[Instance, tuple]:
        inst_hash_key = self.inst_hash_key(inst)
        if inst_hash_key not in self.inst_hash:
            raise DedupNotYetSeenError()

        hash_value = self.inst_hash[inst_hash_key]
        inst = self.inst_dedup[hash_value]

        return inst, hash_value

    def dedup_impl(self, impl: Implementation) -> Tuple[Implementation, tuple]:
        impl_hash_key = self.impl_hash_key(impl)
        if impl_hash_key not in self.impl_hash:
            raise DedupNotYetSeenError()

        hash_value = self.impl_hash[impl_hash_key]
        impl = self.impl_dedup[hash_value]

        return impl, hash_value

    def hash_literal(self, lit: ValueLiteral) -> tuple:
        match lit:
            case IdentLiteral(ExternGlobal(ident)):
                return ("extern", ident)
            case PathLiteral(PathGlobal(path)):
                return ("global", path)
            case AnonymousLiteral(id):
                return ("anonymous", id)
            case ImplementationLiteral(impl):
                dedup_impl, hash_value = self.dedup_impl(impl)
                lit.impl = Implementation(
                    dedup_impl.path, dedup_impl.lambda_id, dedup_impl.continuation_id,
                    impl.arg_literal, impl.ident_captures, impl.anonymous_captures,
                    False
                )
                return ("impl", hash_value, tuple(impl.anonymous_captures))
            case InstanceLiteral(inst):
                lit.inst, hash_value = self.dedup_inst(inst)
                return ("inst", hash_value)
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

    def hash_inst(self, inst: Instance) -> Optional[tuple]:
        try:
            inst.impl, impl_hash_value = self.dedup_impl(inst.impl)

            captures = []
            inst_hash_values = []
            for capture in inst.captures:
                capture, hash_value = self.dedup_inst(capture)

                captures.append(capture)
                inst_hash_values.append(hash_value)

            inst.captures = captures
            return ("inst", impl_hash_value, tuple(inst_hash_values))
        except DedupNotYetSeenError:
            return None

    def hash_inst_def(self, inst_def: InstanceDefinition) -> Optional[tuple]:
        try:
            inst_def.inst, inst_hash_value = self.dedup_inst(inst_def.inst)
            return ("def", inst_hash_value)
        except DedupNotYetSeenError:
            return None

    def hash_crate(self, crate: ExternCrate) -> tuple:
        return ("crate", crate.name)

    def insert_impl(self, impl: Implementation, hash_value: tuple):
        self.impl_hash[self.impl_hash_key(impl)] = hash_value
        if hash_value not in self.impl_dedup:
            self.impl_dedup[hash_value] = impl
            self.implementations.append(impl)

    def insert_inst(self, inst: Instance, hash_value: tuple):
        self.inst_hash[self.inst_hash_key(inst)] = hash_value
        if hash_value not in self.inst_dedup:
            self.inst_dedup[hash_value] = inst
            self.instances.append(inst)

    def insert_inst_def(self, inst_def: InstanceDefinition):
        self.definitions.append(inst_def)

    def insert_crate(self, crate: ExternCrate):
        if crate not in self.extern_crates:
            self.extern_crates.append(crate)

    def deduplicate(self, prog: List[Statement]):
        queue = prog[:]
        while len(queue) > 0:
            for stmt in queue[:]:
                hash_value: Optional[tuple] = None
                match stmt:
                    case ExternCrate() as crate:
                        hash_value = self.hash_crate(crate)
                    case Implementation() as impl:
                        hash_value = self.hash_impl(impl)
                    case Instance() as inst:
                        hash_value = self.hash_inst(inst)
                    case InstanceDefinition() as inst_def:
                        hash_value = self.hash_inst_def(inst_def)

                if hash_value is None:
                    continue
                else:
                    queue.remove(stmt)

                match stmt:
                    case ExternCrate() as crate:
                        self.insert_crate(crate)
                    case Implementation() as impl:
                        self.insert_impl(impl, hash_value)
                    case Instance() as inst:
                        self.insert_inst(inst, hash_value)
                    case InstanceDefinition() as inst_def:
                        self.insert_inst_def(inst_def)

    def dedup_new_inst(self, inst: Instance) -> Instance:
        hash_value = self.hash_inst(inst)
        if hash_value is None:
            raise DedupImplementationsError("cannot deduplicate new instance, captures unknown")

        self.insert_inst(inst, hash_value)
        return self.inst_dedup[hash_value]

def build_dedup_context(prog: List[Statement]) -> DedupImplementationsContext:
    ctx = DedupImplementationsContext()
    ctx.deduplicate(prog)
    return ctx

def collect_dedup_context(ctx: DedupImplementationsContext, tree_shake: bool = False) -> List[Statement]:
    return (
        cast(List[Statement], ctx.extern_crates) +
        cast(List[Statement], ctx.definitions) +
        cast(List[Statement], ctx.implementations) +
        cast(List[Statement], ctx.instances)
    )

def tree_shake_dedup_context(ctx: DedupImplementationsContext) -> List[Statement]:
    inst_counter: DefaultDict[Path, int] = defaultdict(int)
    prog: List[Statement] = []

    def visit_inst_def(inst_def: InstanceDefinition, ctx: DedupImplementationsContext):
        if inst_def in prog:
            return

        visit_inst(inst_def.inst, ctx)

        prog.append(inst_def)

    def visit_inst(inst: Instance, ctx: DedupImplementationsContext):
        if inst in prog:
            return

        visit_impl(inst.impl, ctx)

        for capture in inst.captures:
            visit_inst(capture, ctx)

        prog.append(inst)

    def visit_impl(impl: Implementation, ctx: DedupImplementationsContext):
        if impl in prog:
            return

        match impl:
            case ReturnImplementation() as impl:
                visit_lit(impl.value, ctx)
            case TailCallImplementation() as impl:
                visit_lit(impl.fn, ctx)
                visit_lit(impl.arg, ctx)
            case ContinueCallImplementation() as impl:
                visit_lit(impl.fn, ctx)
                visit_lit(impl.arg, ctx)
                visit_lit(impl.next, ctx)

        prog.append(impl)

    def visit_lit(lit: ValueLiteral, ctx: DedupImplementationsContext):
        match lit:
            case InstanceLiteral(inst):
                inst, _ = ctx.dedup_inst(inst)
                visit_inst(inst, ctx)
            case ImplementationLiteral(impl):
                impl, _ = ctx.dedup_impl(impl)
                visit_impl(impl, ctx)

    for crate in ctx.extern_crates:
        prog.append(crate)

    for inst_def in ctx.definitions:
        visit_inst_def(inst_def, ctx)

    for stmt in prog:
        if not isinstance(stmt, Instance):
            continue

        stmt.inst_id = inst_counter[stmt.path]
        inst_counter[stmt.path] += 1

    return prog

def dedup_implementations(prog: List[Statement]) -> List[Statement]:
    ctx = build_dedup_context(prog)
    return tree_shake_dedup_context(ctx)
