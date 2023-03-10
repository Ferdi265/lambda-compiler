from .definitions import *
import sys

class PrettyMLIRError(Exception):
    pass

def pretty_mlir(prog: List[Statement], file: TextIO = sys.stdout):
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement):
        match stmt:
            case ExternCrate() as crate:
                visit_extern_crate(crate)
            case Implementation() as impl:
                visit_implementation(impl)
            case Instance() as inst:
                visit_instance(inst)
            case InstanceDefinition() as inst_def:
                visit_instance_definition(inst_def)
            case _:
                raise PrettyMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_extern_crate(crate: ExternCrate):
        print(f"extern crate {crate.name};", file=file)

    def visit_implementation(impl: Implementation):
        assert impl.arg_literal is None or impl.arg_literal == AnonymousLiteral(0)
        assert len(impl.ident_captures) == 0

        print(f"impl {impl.path}!{impl.lambda_id}!{impl.continuation_id} = ", end="", file=file)

        match impl:
            case ReturnImplementation() as impl:
                print(f"{visit_literal(impl.value)};", file=file)
            case TailCallImplementation() as impl:
                print(f"{visit_literal(impl.fn)} {visit_literal(impl.arg)};", file=file)
            case ContinueCallImplementation() as impl:
                print(f"{visit_literal(impl.fn)} {visit_literal(impl.arg)} -> {visit_literal(impl.next)};", file=file)
            case _:
                raise PrettyMLIRError(f"unexpected AST node encountered: {impl}")
    def visit_instance(inst: Instance):
        impl = inst.impl
        captures = " ".join(f"{i.path}%{i.inst_id}" for i in inst.captures)
        print(f"inst {inst.path}%{inst.inst_id} = {impl.path}!{impl.lambda_id}!{impl.continuation_id}[{captures}];", file=file)

    def visit_instance_definition(inst_def: InstanceDefinition):
        inst = inst_def.inst
        is_public_str = "pub " if inst_def.is_public else ""
        init_tag = " $$" if inst_def.needs_init else ""
        print(f"{is_public_str}{inst_def.path} = {inst.path}%{inst.inst_id}{init_tag};", file=file)

    def visit_literal(lit: ValueLiteral) -> str:
        match lit:
            case IdentLiteral(ExternGlobal(ident)):
                return f"{ident}"
            case PathLiteral(PathGlobal(path)):
                return f"{path}"
            case AnonymousLiteral(id):
                return f"${id}"
            case ImplementationLiteral(impl):
                captures = " ".join(f"${id}" for id in impl.anonymous_captures)
                return f"{impl.path}!{impl.lambda_id}!{impl.continuation_id}[{captures}]"
            case _:
                raise PrettyMLIRError(f"unexpected AST node encountered: {lit}")

    visit_program(prog)
