from __future__ import annotations
from dataclasses import dataclass, field
from ...ast.mlir_linked import *
from collections import defaultdict

class DedupNotYetSeenError(Exception):
    pass

class DedupMLIRError(Exception):
    pass

@dataclass
class DedupMLIRContext:
    extern_crates: List[ExternCrate] = field(default_factory = list)
    externs: List[Extern] = field(default_factory = list)
    implementations: List[Implementation] = field(default_factory = list)
    instances: List[LinkedInstance] = field(default_factory = list)
    definitions: List[LinkedDefinition] = field(default_factory = list)

    inst_hash: Dict[InstancePath, tuple] = field(default_factory = dict)
    impl_hash: Dict[ImplementationPath, tuple] = field(default_factory = dict)
    inst_dedup: Dict[tuple, LinkedInstance] = field(default_factory = dict)
    impl_dedup: Dict[tuple, Implementation] = field(default_factory = dict)

    def dedup_inst(self, inst: LinkedInstance) -> Tuple[LinkedInstance, tuple]:
        if inst.path not in self.inst_hash:
            raise DedupNotYetSeenError()

        hash_value = self.inst_hash[inst.path]
        inst = self.inst_dedup[hash_value]

        return inst, hash_value

    def dedup_impl(self, impl: Implementation) -> Tuple[Implementation, tuple]:
        if impl.path not in self.impl_hash:
            raise DedupNotYetSeenError()

        hash_value = self.impl_hash[impl.path]
        impl = self.impl_dedup[hash_value]

        return impl, hash_value

    def hash_def(self, defi: LinkedDefinition) -> Optional[tuple]:
        try:
            defi.inst, inst_hash_value = self.dedup_inst(defi.inst)
            return ("def", inst_hash_value)
        except DedupNotYetSeenError:
            return None

    def hash_inst(self, inst: LinkedInstance) -> Optional[tuple]:
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
                    raise DedupMLIRError(f"unexpected AST node encountered: {impl}")
        except DedupNotYetSeenError:
            return None

    def hash_literal(self, lit: ValueLiteral) -> tuple:
        match lit:
            case CaptureLiteral(id):
                return ("cap", id)
            case ExternLiteral(name):
                return ("extern", name)
            case LinkedDefinitionLiteral(defi):
                return ("def", defi.path)
            case LinkedInstanceLiteral(inst):
                lit.inst, hash_value = self.dedup_inst(inst)
                return ("inst", hash_value)
            case LinkedImplementationLiteral(impl, captures):
                lit.impl, hash_value = self.dedup_impl(impl)
                return ("impl", hash_value, tuple(self.hash_capture(cap) for cap in captures))
            case _:
                raise DedupMLIRError(f"unexpected AST node encountered: {lit}")

    def hash_capture(self, cap: int | LinkedInstance) -> int | InstancePath:
        match cap:
            case LinkedInstance():
                return cap.path
            case int():
                return cap

    def hash_crate(self, crate: ExternCrate) -> tuple:
        return ("crate", crate.name)

    def hash_extern(self, extern: Extern) -> tuple:
        return ("extern", extern.name)

    def insert_impl(self, impl: Implementation, hash_value: tuple):
        self.impl_hash[impl.path] = hash_value
        if hash_value not in self.impl_dedup:
            self.impl_dedup[hash_value] = impl
            self.implementations.append(impl)

    def insert_inst(self, inst: LinkedInstance, hash_value: tuple):
        self.inst_hash[inst.path] = hash_value
        if hash_value not in self.inst_dedup:
            self.inst_dedup[hash_value] = inst
            self.instances.append(inst)

    def insert_def(self, defi: LinkedDefinition):
        self.definitions.append(defi)

    def insert_crate(self, crate: ExternCrate):
        if crate not in self.extern_crates:
            self.extern_crates.append(crate)

    def insert_extern(self, extern: Extern):
        if extern not in self.externs:
            self.externs.append(extern)

    def deduplicate(self, prog: List[Statement]):
        queue = prog[:]
        while len(queue) > 0:
            for stmt in queue[:]:
                hash_value: Optional[tuple] = None
                match stmt:
                    case ExternCrate() as crate:
                        hash_value = self.hash_crate(crate)
                    case Extern() as extern:
                        hash_value = self.hash_extern(extern)
                    case Implementation() as impl:
                        hash_value = self.hash_impl(impl)
                    case LinkedInstance() as inst:
                        hash_value = self.hash_inst(inst)
                    case LinkedDefinition() as defi:
                        hash_value = self.hash_def(defi)
                    case _:
                        raise DedupMLIRError(f"unexpected AST node encountered: {stmt}")

                if hash_value is None:
                    continue
                else:
                    queue.remove(stmt)

                match stmt:
                    case ExternCrate() as crate:
                        self.insert_crate(crate)
                    case Extern() as extern:
                        self.insert_extern(extern)
                    case Implementation() as impl:
                        self.insert_impl(impl, hash_value)
                    case LinkedInstance() as inst:
                        self.insert_inst(inst, hash_value)
                    case LinkedDefinition() as defi:
                        self.insert_def(defi)
                    case _:
                        raise DedupMLIRError(f"unexpected AST node encountered: {stmt}")

    def dedup_new_inst(self, inst: LinkedInstance) -> LinkedInstance:
        hash_value = self.hash_inst(inst)
        if hash_value is None:
            raise DedupMLIRError(f"cannot deduplicate new instance, captures unknown: {inst}")

        self.insert_inst(inst, hash_value)
        return self.inst_dedup[hash_value]

    def replace_new_impl(self, new_impl: Implementation, old_impl: Implementation) -> Implementation:
        hash_value = self.hash_impl(new_impl)
        if hash_value is None:
            raise DedupMLIRError(f"cannot replace impl, references unknown: {new_impl}")

        self.insert_impl(new_impl, hash_value)

        old_hash_value = self.impl_hash[old_impl.path]
        self.impl_hash[old_impl.path] = hash_value
        self.impl_dedup[old_hash_value] = new_impl
        return new_impl

    @staticmethod
    def build(prog: List[Statement]) -> DedupMLIRContext:
        ctx = DedupMLIRContext()
        ctx.deduplicate(prog)
        return ctx

    def collect(self) -> List[Statement]:
        return (
            cast(List[Statement], self.extern_crates) +
            cast(List[Statement], self.externs) +
            cast(List[Statement], self.definitions) +
            cast(List[Statement], self.implementations) +
            cast(List[Statement], self.instances)
        )

    def tree_shake(self, opt_deps: Optional[List[Statement]] = None) -> List[Statement]:
        inst_counter: DefaultDict[Path, int] = defaultdict(int)
        prog: List[Statement] = []
        deps = opt_deps or []

        def visit_def(defi: LinkedDefinition):
            if defi in deps:
                return
            if defi in prog:
                return

            defi.inst, _ = self.dedup_inst(defi.inst)
            visit_inst(defi.inst)

            prog.append(defi)

        def visit_inst(inst: LinkedInstance):
            if inst in deps:
                return
            if inst in prog:
                return

            inst.impl, _ = self.dedup_impl(inst.impl)
            visit_impl(inst.impl)

            for i, capture in enumerate(inst.captures):
                capture, _ = self.dedup_inst(capture)
                inst.captures[i] = capture
                visit_inst(capture)

            prog.append(inst)

        def visit_impl(impl: Implementation):
            impl, _ = self.dedup_impl(impl)

            if impl in deps:
                return
            if impl in prog:
                return

            match impl:
                case ReturnImplementation() as impl:
                    visit_lit(impl.value)
                case TailCallImplementation() as impl:
                    visit_lit(impl.fn)
                    visit_lit(impl.arg)
                case ContinueCallImplementation() as impl:
                    visit_lit(impl.fn)
                    visit_lit(impl.arg)
                    visit_lit(impl.next)
                case _:
                    raise DedupMLIRError(f"unexpected AST node encountered: {impl}")

            prog.append(impl)

        def visit_lit(lit: ValueLiteral):
            match lit:
                case LinkedDefinitionLiteral(defi):
                    visit_def(defi)
                case LinkedInstanceLiteral(inst):
                    inst, _ = self.dedup_inst(inst)
                    lit.inst = inst
                    visit_inst(inst)
                case LinkedImplementationLiteral(impl, captures):
                    impl, _ = self.dedup_impl(impl)
                    lit.impl = impl
                    visit_impl(impl)
                    for i, cap in enumerate(captures):
                        if isinstance(cap, LinkedInstance):
                            cap, _ = self.dedup_inst(cap)
                            captures[i] = cap
                            visit_inst(cap)
                case ExternLiteral() as ext:
                    visit_extern(ext)

        def visit_extern(ext: ExternLiteral):
            for stmt in prog:
                if isinstance(stmt, Extern) and stmt.name == ext.name:
                    return

            prog.append(Extern(ext.name))


        for crate in self.extern_crates:
            prog.append(crate)

        for defi in self.definitions:
            visit_def(defi)

        for stmt in prog:
            if not isinstance(stmt, LinkedInstance):
                continue

            stmt.path = InstancePath(stmt.path.path, inst_counter[stmt.path.path])
            inst_counter[stmt.path.path] += 1

        return prog

def dedup_mlir(prog: List[Statement], opt_deps: Optional[List[Statement]] = None) -> List[Statement]:
    deps = opt_deps or []
    ctx = DedupMLIRContext.build(deps + prog)
    return ctx.tree_shake(deps)
