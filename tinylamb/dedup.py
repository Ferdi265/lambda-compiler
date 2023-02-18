from __future__ import annotations
from typing import *

from .instantiate import *

class DedupNotYetSeenError(Exception):
    pass

class DedupImplementationsError(Exception):
    pass

@dataclass
class DedupImplementationsContext:
    implementations: List[Implementation] = field(default_factory = list)
    instances: List[Instance] = field(default_factory = list)
    definitions: List[InstanceDefinition] = field(default_factory = list)

    inst_hash: Dict[Tuple[str, int], tuple] = field(default_factory = dict)
    impl_hash: Dict[Tuple[str, int, int], tuple] = field(default_factory = dict)
    inst_dedup: Dict[tuple, Instance] = field(default_factory = dict)
    impl_dedup: Dict[tuple, Implementation] = field(default_factory = dict)

    def inst_hash_key(self, inst: Instance) -> Tuple[str, int]:
        return (inst.name, inst.inst_id)

    def impl_hash_key(self, impl: Implementation) -> Tuple[str, int, int]:
        return (impl.name, impl.lambda_id, impl.continuation_id)

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
            case IdentLiteral(Global(ident)):
                return ("global", ident)
            case AnonymousLiteral(id):
                return ("anonymous", id)
            case ImplementationLiteral(impl):
                lit.impl, hash_value = self.dedup_impl(impl)
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

    def deduplicate(self, prog: List[Statement]):
        print("before:", len(prog))

        queue = prog
        while len(queue) > 0:
            for stmt in queue[:]:
                hash_value: Optional[tuple] = None
                match stmt:
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
                    case Implementation() as impl:
                        self.insert_impl(impl, hash_value)
                    case Instance() as inst:
                        self.insert_inst(inst, hash_value)
                    case InstanceDefinition() as inst_def:
                        self.definitions.append(inst_def)

        print("after:", len(self.implementations) + len(self.instances) + len(self.definitions))

def dedup_implementations(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        ctx = DedupImplementationsContext()
        ctx.deduplicate(prog)
        return cast(List[Statement], ctx.implementations) + cast(List[Statement], ctx.instances) + cast(List[Statement], ctx.definitions)

    return visit_program(prog)
