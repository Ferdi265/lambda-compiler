from .collect_mlir import *
from .instantiate import *

class ResolveMLIRError(Exception):
    pass

def resolve_mlir(prog: List[Statement], deps: Optional[List[Statement]] = None) -> List[Statement]:
    inst_table: Dict[InstancePath, Instance] = {}
    impl_table: Dict[ImplementationPath, Implementation] = {}

    if deps is None:
        deps = []

    def visit_deps_program(prog: List[Statement]):
        for stmt in prog:
            visit_deps_statement(stmt)

    def visit_deps_statement(stmt: Statement):
        match stmt:
            case ExternCrate():
                pass
            case InstanceDefinition() as inst_def:
                pass
            case Instance() as inst:
                inst_table[InstancePath(inst.path, inst.inst_id)] = inst
            case Implementation() as impl:
                impl_table[ImplementationPath(impl.path, impl.lambda_id, impl.continuation_id)] = impl
            case _:
                raise ResolveMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement) -> Statement:
        match stmt:
            case ExternCrate():
                return stmt
            case MInstanceDefinition() as inst_def:
                return visit_instance_definition(inst_def)
            case MInstance() as inst:
                return visit_instance(inst)
            case MImplementation() as impl:
                return visit_implementation(impl)
            case _:
                raise ResolveMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_instance_definition(inst_def: MInstanceDefinition) -> InstanceDefinition:
        inst = inst_table[inst_def.inst]

        return InstanceDefinition(
            inst_def.path, inst, inst_def.needs_init, inst_def.is_public
        )

    def visit_instance(inst: MInstance) -> Instance:
        assert inst.path not in inst_table, "duplicate instance"
        impl = impl_table[inst.impl]
        captures = [inst_table[cap] for cap in inst.captures]

        new_inst = Instance(
            inst.path.path, inst.path.inst_id, impl, captures
        )
        inst_table[inst.path] = new_inst
        return new_inst

    def visit_implementation(impl: MImplementation) -> Implementation:
        assert impl.path not in impl_table, "duplicate Implementation"

        impl_metadata: Tuple[Path, int, int, ValueLiteral, List[str], List[int], bool] = (
            impl.path.path, impl.path.lambda_id, impl.path.continuation_id,
            AnonymousLiteral(0), [], impl.captures, False
        )
        match impl:
            case MReturnImplementation():
                return ReturnImplementation(
                    *impl_metadata,
                    visit_literal(impl.value)
                )
            case MTailCallImplementation():
                return TailCallImplementation(
                    *impl_metadata,
                    visit_literal(impl.fn),
                    visit_literal(impl.arg)
                )
            case MContinueCallImplementation():
                return ContinueCallImplementation(
                    *impl_metadata,
                    visit_literal(impl.fn),
                    visit_literal(impl.arg),
                    visit_literal(impl.next)
                )
            case _:
                raise ResolveMLIRError(f"unexpected AST node encountered: {impl}")

    def visit_literal(lit: ValueLiteral) -> ValueLiteral:
        match lit:
            case IdentLiteral(ExternGlobal(name)):
                return lit
            case PathLiteral(PathGlobal(path)):
                return lit
            case MInstanceLiteral(inst):
                return InstanceLiteral(inst_table[inst])
            case MImplementationLiteral(impl):
                return ImplementationLiteral(Implementation(
                    impl.path.path, impl.path.lambda_id, impl.path.continuation_id,
                    AnonymousLiteral(0), [], impl.captures, False
                ))
            case _:
                raise ResolveMLIRError(f"unexpected AST node encountered: {lit}")

    visit_deps_program(deps)
    return visit_program(prog)
