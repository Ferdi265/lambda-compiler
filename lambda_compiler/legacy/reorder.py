from .renumber import *

class ReorderImplementationsError(Exception):
    pass

def reorder_implementations(prog: List[Statement]) -> List[Statement]:
    impl_table: Dict[Tuple[Path, int, int], Implementation] = {}

    def visit_program_find_impls(prog: List[Statement]):
        for stmt in prog:
            visit_statement_find_impls(stmt)

    def visit_statement_find_impls(stmt: Statement):
        match stmt:
            case ExternCrate() | Extern():
                pass
            case Implementation() as impl:
                impl_table[(impl.path, impl.lambda_id, impl.continuation_id)] = impl
            case _:
                raise ReorderImplementationsError(f"unexpected AST node encountered: {stmt}")

    reordered: List[Statement] = []
    def visit_program_reorder(prog: List[Statement]):
        for stmt in prog:
            visit_statement_reorder(stmt)

    def visit_statement_reorder(stmt: Statement):
        match stmt:
            case ExternCrate() | Extern():
                reordered.append(stmt)
            case Implementation() as impl:
                visit_implementation_reorder(impl)
            case _:
                raise ReorderImplementationsError(f"unexpected AST node encountered: {stmt}")

    def visit_implementation_reorder(impl: Implementation):
        if impl in reordered:
            return

        match impl:
            case ReturnImplementation():
                visit_literal_reorder(impl.value)
            case TailCallImplementation():
                visit_literal_reorder(impl.fn)
                visit_literal_reorder(impl.arg)
            case ContinueCallImplementation():
                visit_literal_reorder(impl.fn)
                visit_literal_reorder(impl.arg)
                visit_literal_reorder(impl.next)

        reordered.append(impl)

    def visit_literal_reorder(lit: ValueLiteral):
        match lit:
            case ImplementationLiteral(impl):
                impl = impl_table[(impl.path, impl.lambda_id, impl.continuation_id)]
                visit_implementation_reorder(impl)

    visit_program_find_impls(prog)
    visit_program_reorder(prog)
    return reordered

