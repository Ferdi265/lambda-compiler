from typing import *
from ..ast.mlir import *
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
            case Extern() as ext:
                visit_extern(ext)
            case Definition() as defi:
                visit_definition(defi)
            case Instance() as inst:
                visit_instance(inst)
            case Implementation() as impl:
                visit_implementation(impl)
            case _:
                raise PrettyMLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_extern_crate(crate: ExternCrate):
        print(f"extern crate {crate.name};", file=file)

    def visit_extern(ext: Extern):
        print(f"extern {ext.name};", file=file)

    def visit_definition(defi: Definition):
        inst = defi.inst
        is_public_str = "pub " if defi.is_public else ""
        init_tag = " $$" if defi.needs_init else ""
        print(f"{is_public_str}{defi.path} = {inst.path}{init_tag};", file=file)

    def visit_instance(inst: Instance):
        impl = inst.impl
        captures = " ".join(f"{cap}" for cap in inst.captures)
        print(f"inst {inst.path} = {impl}[{captures}];", file=file)

    def visit_implementation(impl: Implementation):
        print(f"impl {impl.path} = ", end="", file=file)

        match impl:
            case ReturnImplementation() as impl:
                print(f"{visit_literal(impl.value)};", file=file)
            case TailCallImplementation() as impl:
                print(f"{visit_literal(impl.fn)} {visit_literal(impl.arg)};", file=file)
            case ContinueCallImplementation() as impl:
                print(f"{visit_literal(impl.fn)} {visit_literal(impl.arg)} -> {visit_literal(impl.next)};", file=file)
            case _:
                raise PrettyMLIRError(f"unexpected AST node encountered: {impl}")

    def visit_literal(lit: ValueLiteral) -> str:
        match lit:
            case CaptureLiteral(id):
                return f"${id}"
            case ExternLiteral(name):
                return f"{name}"
            case DefinitionLiteral(path):
                return f"{path}"
            case InstanceLiteral(inst):
                return f"{inst}"
            case ImplementationLiteral(impl, captures):
                fmt_captures = " ".join(visit_capture(cap) for cap in captures)
                return f"{impl}[{fmt_captures}]"
            case _:
                raise PrettyMLIRError(f"unexpected AST node encountered: {lit}")

    def visit_capture(cap: int | InstancePath) -> str:
        match cap:
            case InstancePath():
                return f"{cap}"
            case int():
                return f"${cap}"

    visit_program(prog)
