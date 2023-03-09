from __future__ import annotations
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

class AddDefinitionsError(Exception):
    pass

def add_definitions(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        new_prog = []
        for stmt in prog:
            new_prog.append(stmt)
            new_prog += visit_statement(stmt)
        return new_prog

    def visit_statement(stmt: Statement) -> List[Statement]:
        match stmt:
            case Implementation() as impl:
                return visit_implementation(impl)
            case _:
                return []

    def visit_implementation(impl: Implementation) -> List[Statement]:
        if impl.lambda_id != 0 or impl.continuation_id != 0:
            return []

        if len(impl.anonymous_captures) != 0:
            raise AddDefinitionsError(f"initial implementation must not have captures! {impl}")

        inst = Instance(impl.path, 0, impl, [])
        inst_def = InstanceDefinition(impl.path, inst, needs_init=True, is_public=impl.is_public)
        return [inst, inst_def]

    return visit_program(prog)
