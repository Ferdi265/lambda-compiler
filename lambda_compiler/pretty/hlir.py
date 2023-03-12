from typing import *
from ..ast.hlir import *
import sys

class PrettyHLIRError(Exception):
    pass

def pretty_hlir(prog: List[Statement], file: TextIO = sys.stdout, stub: bool = False):
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement):
        match stmt:
            case ExternCrate(crate):
                print(f"extern crate {crate};", file=file)
            case Extern(name):
                if stub:
                    return
                print(f"extern impure {name};", file=file)
            case Assignment(path, value, is_public, is_impure):
                if stub and not is_public:
                    return
                is_public_str = "pub " if is_public else ""
                is_impure_str = "impure " if is_impure else ""
                print(f"{is_public_str}{is_impure_str}{path} = ", end="", file=file)
                visit_expr(value)
                print(";", file=file)
            case Alias(path, target, is_public):
                if stub and not is_public:
                    return
                is_public_str = "pub " if is_public else ""
                print(f"{is_public_str}{path} = use {target};", file=file)
            case _:
                raise PrettyHLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_expr(expr: Expr):
        if stub:
            print("...", end="", file=file)
            return

        match expr:
            case Paren(inner):
                print("(", end="", file=file)
                visit_expr(inner)
                print(")", end="", file=file)
            case Call(fn, arg):
                visit_expr(fn)
                print(" ", end="", file=file)
                visit_expr(arg)
            case Lambda(name, body):
                print(f"{name} -> ", end="", file=file)
                visit_expr(body)
            case Ident(name):
                print(f"{name}", end="", file=file)
            case Absolute(path):
                print(f"{path}", end="", file=file)
            case _:
                raise PrettyHLIRError(f"unexpected AST node encountered: {expr}")

    visit_program(prog)
