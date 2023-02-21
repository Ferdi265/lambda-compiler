from .ast import *
from .resolve import *
from .rechain import *
from .continuations import *
from .flattenimpls import *
from .instantiate import *
import sys

class PrettyError(Exception):
    pass

def pretty(prog: List[Statement]):
    indent = lambda depth: "    " * depth

    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt, 0) for stmt in prog]

    def visit_statement(stmt: Statement, depth: int):
        match stmt:
            case ExternCrate(crate):
                print(f"{indent(depth)}ExternCrate({crate})")
            case Extern(name):
                print(f"{indent(depth)}Extern({name})")
            case ContinuationAssignment(name, value):
                print(f"{indent(depth)}CAssignment")
                print(f"{indent(depth)}- name: {name!r}")
                print(f"{indent(depth)}- value:")
                visit_expr(value, depth + 1)
            case NameAssignment(name, value):
                print(f"{indent(depth)}Assignment")
                print(f"{indent(depth)}- name: {name!r}")
                print(f"{indent(depth)}- value:")
                visit_expr(value, depth + 1)
            case PathAssignment(path, value):
                print(f"{indent(depth)}Assignment")
                print(f"{indent(depth)}- path: {path}")
                print(f"{indent(depth)}- value:")
                visit_expr(value, depth + 1)
            case Implementation() as impl:
                visit_implementation(impl, depth)

    def visit_expr(expr: Expr, depth: int):
        match expr:
            case Paren(inner):
                print(f"{indent(depth)}Paren")
                visit_expr(inner, depth + 1)
            case Call(fn, arg):
                print(f"{indent(depth)}Call")
                print(f"{indent(depth)}- fn:")
                visit_expr(fn, depth + 1)
                print(f"{indent(depth)}- arg:")
                visit_expr(arg, depth + 1)
            case CallStart() as call:
                visit_call_start(call, depth)
            case ContinuationChain() as chain:
                visit_continuation_chain(chain, depth)
            case Lambda(name, body, captures):
                print(f"{indent(depth)}Lambda")
                print(f"{indent(depth)}- name: {name!r}")
                print(f"{indent(depth)}- captures: {captures}")
                print(f"{indent(depth)}- body:")
                visit_expr(body, depth + 1)
            case CLambda(name, body, captures):
                print(f"{indent(depth)}CLambda")
                print(f"{indent(depth)}- name: {name!r}")
                print(f"{indent(depth)}- captures: {captures}")
                print(f"{indent(depth)}- body:")
                visit_expr(body, depth + 1)
            case Local(name):
                print(f"{indent(depth)}Local({name!r})")
            case ExternGlobal(name):
                print(f"{indent(depth)}ExternGlobal({name!r})")
            case Ident(name):
                print(f"{indent(depth)}Ident({name!r})")
            case PathGlobal(path):
                print(f"{indent(depth)}PathGlobal({path})")
            case PathExpr(path):
                print(f"{indent(depth)}PathExpr({path})")

    def visit_literal(lit: ValueLiteral, depth: int):
        match lit:
            case IdentLiteral(Local(name)):
                print(f"{indent(depth)}Local({name!r})")
            case IdentLiteral(ExternGlobal(name)):
                print(f"{indent(depth)}ExternGlobal({name!r})")
            case IdentLiteral(Ident(name)):
                print(f"{indent(depth)}Ident({name!r})")
            case PathLiteral(PathGlobal(path)):
                print(f"{indent(depth)}PathGlobal({path})")
            case PathLiteral(PathExpr(path)):
                print(f"{indent(depth)}PathExpr({path})")
            case AnonymousLiteral(id):
                print(f"{indent(depth)}Anonymous({id})")
            case LambdaLiteral(lamb):
                visit_expr(lamb, depth)
            case ImplementationLiteral(impl):
                print(f"{indent(depth)}Implementation({impl.path}, {impl.lambda_id}, {impl.continuation_id})")
                if len(impl.ident_captures) != 0:
                    print(f"{indent(depth)}- ident_captures: {impl.ident_captures}")
                if len(impl.anonymous_captures) != 0:
                    print(f"{indent(depth)}- anonymous_captures: {impl.anonymous_captures}")

    def visit_call_start(call: CallStart, depth: int):
        print(f"{indent(depth)}CallChain")
        print(f"{indent(depth)}- 0:")
        visit_expr(call.fn, depth + 1)
        print(f"{indent(depth)}- 1:")
        visit_expr(call.arg, depth + 1)

        cur = call.next
        i = 2
        while cur is not None:
            print(f"{indent(depth)}- {i}:")
            visit_expr(cur.arg, depth + 1)
            cur = cur.next
            i += 1

    def visit_continuation_chain(chain: ContinuationChain, depth: int):
        print(f"{indent(depth)}ContinuationChain")
        for i, cont in enumerate(chain.continuations):
            print(f"{indent(depth)}- {i}:")
            print(f"{indent(depth + 1)}- id: {cont.id}")
            print(f"{indent(depth + 1)}- ident_captures: {cont.ident_captures}")
            print(f"{indent(depth + 1)}- anonymous_captures: {cont.anonymous_captures}")
            print(f"{indent(depth + 1)}- fn:")
            visit_literal(cont.fn, depth + 2)
            print(f"{indent(depth + 1)}- arg:")
            visit_literal(cont.arg, depth + 2)

        print(f"{indent(depth)}- result:")
        visit_literal(chain.result_literal, depth + 1)

    def visit_implementation(impl: Implementation, depth: int):
        print(f"{indent(depth)}{type(impl).__name__}({impl.path}, {impl.lambda_id}, {impl.continuation_id})")
        if impl.arg_literal is not None:
            print(f"{indent(depth)}- arg_literal:")
            visit_literal(impl.arg_literal, depth + 1)
        if len(impl.ident_captures) != 0:
            print(f"{indent(depth)}- ident_captures: {impl.ident_captures}")
        if len(impl.anonymous_captures) != 0:
            print(f"{indent(depth)}- anonymous_captures: {impl.anonymous_captures}")

        match impl:
            case ReturnImplementation() as impl:
                print(f"{indent(depth)}- value:")
                visit_literal(impl.value, depth + 1)
            case TailCallImplementation() as impl:
                print(f"{indent(depth)}- fn:")
                visit_literal(impl.fn, depth + 1)
                print(f"{indent(depth)}- arg:")
                visit_literal(impl.arg, depth + 1)
            case ContinueCallImplementation() as impl:
                print(f"{indent(depth)}- fn:")
                visit_literal(impl.fn, depth + 1)
                print(f"{indent(depth)}- arg:")
                visit_literal(impl.arg, depth + 1)
                print(f"{indent(depth)}- next:")
                visit_literal(impl.next, depth + 1)

    visit_program(prog)

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
                raise PrettyError(f"unexpected AST node encountered: {stmt}")

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
                raise PrettyError(f"unexpected AST node encountered: {expr}")

    visit_program(prog)

def pretty_mlir(prog: List[Statement], file: TextIO = sys.stdout):
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement):
        match stmt:
            case Implementation() as impl:
                visit_implementation(impl)
            case Instance() as inst:
                visit_instance(inst)
            case InstanceDefinition() as inst_def:
                visit_instance_definition(inst_def)
            case _:
                raise PrettyError(f"unexpected AST node encountered: {stmt}")

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
                raise PrettyError(f"unexpected AST node encountered: {impl}")

    def visit_instance(inst: Instance):
        impl = inst.impl
        captures = " ".join(f"{i.path}%{i.inst_id}" for i in inst.captures)
        print(f"inst {inst.path}%{inst.inst_id} = {impl.path}!{impl.lambda_id}!{impl.continuation_id}[{captures}];", file=file)

    def visit_instance_definition(inst_def: InstanceDefinition):
        inst = inst_def.inst
        init_tag = " $$" if inst_def.needs_init else ""
        print(f"pub {inst_def.path} = {inst.path}%{inst.inst_id}{init_tag};", file=file)

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
            case InstanceLiteral(inst):
                return f"{inst.path}%{inst.inst_id}"
            case _:
                raise PrettyError(f"unexpected AST node encountered: {lit}")

    visit_program(prog)
