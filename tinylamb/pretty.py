from .ast import *
from .resolve import *
from .rechain import *
from .continuations import *
from .flattenimpls import *

def pretty(prog: List[Statement]):
    indent = lambda depth: "    " * depth

    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt, 0) for stmt in prog]

    def visit_statement(stmt: Statement, depth: int):
        match stmt:
            case ContinuationAssignment(name, value):
                print(f"{indent(depth)}ContinuationAssignment")
                print(f"{indent(depth)}- name: {name!r}")
                print(f"{indent(depth)}- value:")
                visit_expr(value, depth + 1)
            case Assignment(name, value):
                print(f"{indent(depth)}Assignment")
                print(f"{indent(depth)}- name: {name!r}")
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
            case ContinuationLambda(name, body, captures):
                print(f"{indent(depth)}ContinuationLambda")
                print(f"{indent(depth)}- name: {name!r}")
                print(f"{indent(depth)}- captures: {captures}")
                print(f"{indent(depth)}- body:")
                visit_expr(body, depth + 1)
            case Local(name):
                print(f"{indent(depth)}Local({name!r})")
            case Global(name):
                print(f"{indent(depth)}Global({name!r})")
            case Ident(name):
                print(f"{indent(depth)}Ident({name!r})")

    def visit_literal(lit: ValueLiteral, depth: int):
        match lit:
            case IdentLiteral(Local(name)):
                print(f"{indent(depth)}Local({name!r})")
            case IdentLiteral(Global(name)):
                print(f"{indent(depth)}Global({name!r})")
            case IdentLiteral(Ident(name)):
                print(f"{indent(depth)}Ident({name!r})")
            case AnonymousLiteral(id):
                print(f"{indent(depth)}Anonymous({id})")
            case LambdaLiteral(lamb):
                visit_expr(lamb, depth)
            case ImplementationLiteral(impl):
                print(f"{indent(depth)}Implementation({impl.name!r}, {impl.lambda_id}, {impl.continuation_id})")
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
        print(f"{indent(depth)}{type(impl).__name__}({impl.name!r}, {impl.lambda_id}, {impl.continuation_id})")
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
