from .resolve import *
import sys

class PrettyHLIRError(Exception):
    pass

def pretty_hlir(prog: List[Statement], file: TextIO = sys.stdout):
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement):
        match stmt:
            case ExternCrate(crate):
                print(f"extern crate {crate};", file=file)
            case Extern(name):
                print(f"extern {name};", file=file)
            case NameAssignment(name, value):
                print(f"{name} = ", end="", file=file)
                visit_expr(value)
                print(";", file=file)
            case PathAssignment(path, value):
                print(f"{path} = ", end="", file=file)
                visit_expr(value)
                print(";", file=file)
            case _:
                raise PrettyHLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_expr(expr: Expr):
        match expr:
            case Paren(inner):
                print("(", end="", file=file)
                visit_expr(inner)
                print(")", end="", file=file)
            case Call(fn, arg):
                visit_expr(fn)
                print(" ", end="", file=file)
                visit_expr(arg)
            case Lambda(name, body, captures):
                print(f"{name} -> ", end="", file=file)
                visit_expr(body)
            case Ident(name):
                print(f"{name}", end="", file=file)
            case PathExpr(path):
                print(f"{path}", end="", file=file)
            case _:
                raise PrettyHLIRError(f"unexpected AST node encountered: {expr}")

    visit_program(prog)
