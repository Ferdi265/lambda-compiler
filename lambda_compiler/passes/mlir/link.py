from ...ast.mlir_linked import *

class LinkMLIRError(Exception):
    pass

def link_mlir(prog: List[Statement], deps: Optional[List[Statement]] = None) -> List[Statement]:
    def_table: Dict[Path, LinkedDefinition] = {}
    inst_table: Dict[InstancePath, LinkedInstance] = {}
    impl_table: Dict[ImplementationPath, Implementation] = {}

    if deps is None:
        deps = []

    def visit_deps_program(prog: List[Statement]):
        for stmt in prog:
            visit_deps_statement(stmt)

    def visit_deps_statement(stmt: Statement):
        match stmt:
            case ExternCrate() | Extern():
                pass
            case LinkedDefinition() as defi:
                def_table[defi.path] = defi
            case LinkedInstance() as inst:
                inst_table[inst.path] = inst
            case Implementation() as impl:
                impl_table[impl.path] = impl
            case _:
                raise LinkMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement) -> Statement:
        match stmt:
            case ExternCrate() | Extern():
                return stmt
            case Definition() as defi:
                return visit_definition(defi)
            case Instance() as inst:
                return visit_instance(inst)
            case Implementation() as impl:
                return visit_implementation(impl)
            case _:
                raise LinkMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_definition(defi: Definition) -> LinkedDefinition:
        inst = inst_table[defi.inst]

        new_defi = LinkedDefinition(
            defi.path, inst, defi.needs_init, defi.is_public
        )
        def_table[defi.path] = new_defi
        return new_defi

    def visit_instance(inst: Instance) -> LinkedInstance:
        assert inst.path not in inst_table, "duplicate instance"
        impl = impl_table[inst.impl]
        captures = [inst_table[cap] for cap in inst.captures]

        new_inst = LinkedInstance(
            inst.path, impl, captures
        )
        inst_table[inst.path] = new_inst
        return new_inst

    def visit_implementation(impl: Implementation) -> Implementation:
        assert impl.path not in impl_table, "duplicate Implementation"

        impl_metadata: Tuple[ImplementationPath, List[int]] = (
            impl.path, impl.captures
        )
        new_impl: Implementation
        match impl:
            case ReturnImplementation():
                new_impl = ReturnImplementation(
                    *impl_metadata,
                    visit_literal(impl.value)
                )
            case TailCallImplementation():
                new_impl = TailCallImplementation(
                    *impl_metadata,
                    visit_literal(impl.fn),
                    visit_literal(impl.arg)
                )
            case ContinueCallImplementation():
                new_impl = ContinueCallImplementation(
                    *impl_metadata,
                    visit_literal(impl.fn),
                    visit_literal(impl.arg),
                    visit_literal(impl.next)
                )
            case _:
                raise LinkMLIRError(f"unexpected AST node encountered: {impl}")

        impl_table[impl.path] = new_impl
        return new_impl

    def visit_literal(lit: ValueLiteral) -> ValueLiteral:
        match lit:
            case CaptureLiteral() | ExternLiteral():
                return lit
            case DefinitionLiteral(path):
                return LinkedDefinitionLiteral(def_table[path])
            case InstanceLiteral(inst):
                return LinkedInstanceLiteral(inst_table[inst])
            case ImplementationLiteral(impl, captures):
                return LinkedImplementationLiteral(
                    impl_table[impl],
                    [visit_capture(cap) for cap in captures]
                )
            case _:
                raise LinkMLIRError(f"unexpected AST node encountered: {lit}")

    def visit_capture(cap: int | InstancePath) -> int | LinkedInstance:
        match cap:
            case InstancePath():
                return inst_table[cap]
            case int():
                return cap

    visit_deps_program(deps)
    return visit_program(prog)

def unlink_mlir(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement) -> Statement:
        match stmt:
            case ExternCrate() | Extern():
                return stmt
            case LinkedDefinition() as defi:
                return visit_definition(defi)
            case LinkedInstance() as inst:
                return visit_instance(inst)
            case Implementation() as impl:
                return visit_implementation(impl)
            case _:
                raise LinkMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_definition(defi: LinkedDefinition) -> Definition:
        return Definition(
            defi.path, defi.inst.path, defi.needs_init, defi.is_public
        )

    def visit_instance(inst: LinkedInstance) -> Instance:
        return Instance(
            inst.path, inst.impl.path, [cap.path for cap in inst.captures]
        )

    def visit_implementation(impl: Implementation) -> Implementation:
        impl_metadata: Tuple[ImplementationPath, List[int]] = (
            impl.path, impl.captures
        )
        new_impl: Implementation
        match impl:
            case ReturnImplementation():
                return ReturnImplementation(
                    *impl_metadata,
                    visit_literal(impl.value)
                )
            case TailCallImplementation():
                return TailCallImplementation(
                    *impl_metadata,
                    visit_literal(impl.fn),
                    visit_literal(impl.arg)
                )
            case ContinueCallImplementation():
                return ContinueCallImplementation(
                    *impl_metadata,
                    visit_literal(impl.fn),
                    visit_literal(impl.arg),
                    visit_literal(impl.next)
                )
            case _:
                raise LinkMLIRError(f"unexpected AST node encountered: {impl}")

    def visit_literal(lit: ValueLiteral) -> ValueLiteral:
        match lit:
            case CaptureLiteral() | ExternLiteral():
                return lit
            case LinkedDefinitionLiteral(defi):
                return DefinitionLiteral(defi.path)
            case LinkedInstanceLiteral(inst):
                return InstanceLiteral(inst.path)
            case LinkedImplementationLiteral(impl, captures):
                return ImplementationLiteral(
                    impl.path,
                    [visit_capture(cap) for cap in captures]
                )
            case _:
                raise LinkMLIRError(f"unexpected AST node encountered: {lit}")

    def visit_capture(cap: int | LinkedInstance) -> int | InstancePath:
        match cap:
            case LinkedInstance():
                return cap.path
            case int():
                return cap

    return visit_program(prog)
