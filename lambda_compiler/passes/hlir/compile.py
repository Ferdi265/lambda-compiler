from __future__ import annotations
from collections import defaultdict
from ...ast.hlir import *
from ...ast import mlir

class CompileHLIRError(Exception):
    pass

@dataclass
class ValueLiteral:
    pass

@dataclass
class NamedCaptureLiteral(ValueLiteral):
    name: str

@dataclass
class TemporaryCaptureLiteral(ValueLiteral):
    id: int

@dataclass
class ExternLiteral(ValueLiteral):
    name: str

@dataclass
class DefinitionLiteral(ValueLiteral):
    path: Path

@dataclass
class LambdaLiteral(ValueLiteral):
    id: int
    captures: List[str]

@dataclass
class ContinuationLiteral(ValueLiteral):
    id: int
    captures: List[int | str]

@dataclass
class SerializedCall:
    fn: ValueLiteral
    arg: ValueLiteral
    res: int
    param: Optional[str | int]

@dataclass
class SerializedCallResult:
    value: ValueLiteral
    param: Optional[str | int]

@dataclass
class LambdaContext:
    path: Path
    id: int
    scope: List[str]

    temp_id: int = 0
    calls: List[SerializedCall] = field(default_factory = list)
    impls: List[mlir.Implementation] = field(default_factory = list)

    def get_temp_capture_literal(self) -> TemporaryCaptureLiteral:
        lit = TemporaryCaptureLiteral(self.temp_id)
        self.temp_id += 1
        return lit

    def get_serialized_call_param(self, id: int) -> Optional[str | int]:
        if id > 0:
            return id - 1
        elif len(self.scope) > 0:
            return self.scope[0]
        else:
            return None

    def get_serialized_call_result(self, lit: ValueLiteral) -> SerializedCallResult:
        return SerializedCallResult(lit, self.get_serialized_call_param(self.temp_id))

    def sort_captures(self, captures: Set[Optional[int | str]]) -> List[Optional[int | str]]:
        capture_list = list(captures)
        def sort_key(v: Optional[int | str]):
            match v:
                case int():
                    return -v - 1
                case str():
                    return self.scope.index(v) + 1
                case _:
                    return 0
        capture_list.sort(key = sort_key)
        return capture_list

    def anonymize_captures(self, captures: List[Optional[int | str]]) -> List[int]:
        return list(range(1, len(captures) + 1))

def compile_hlir(prog: List[Statement]) -> List[mlir.Statement]:
    lambda_id_table: DefaultDict[Path, int] = defaultdict(int)
    def get_lambda_id(path: Path) -> int:
        id = lambda_id_table[path]
        lambda_id_table[path] += 1
        return id

    def visit_program(prog: List[Statement]) -> List[mlir.Statement]:
        mlir = []
        for stmt in prog:
            mlir += visit_statement(stmt)
        return mlir

    def visit_statement(stmt: Statement) -> List[mlir.Statement]:
        match stmt:
            case ExternCrate(name):
                return [mlir.ExternCrate(name)]
            case Extern(name):
                return [mlir.Extern(name)]
            case Assignment() as ass:
                return visit_assignment(ass)
            case Alias():
                return []
            case _:
                raise CompileHLIRError(f"unexpected AST node encountered: {stmt}")

    def visit_assignment(ass: Assignment) -> List[mlir.Statement]:
        ctx = LambdaContext(ass.path, get_lambda_id(ass.path), [])
        impl, captures = visit_body_expr(ass.value, ctx)
        inst = mlir.Instance(InstancePath(ass.path, 0), impl.path, [])
        defi = mlir.Definition(ass.path, inst.path, needs_init=True, is_public=ass.is_public)
        return ctx.impls + [inst, defi]

    def visit_expr(expr: Expr, ctx: LambdaContext) -> ValueLiteral:
        match expr:
            case Paren(inner):
                return visit_expr(inner, ctx)
            case Ident(name):
                if name in ctx.scope:
                    return NamedCaptureLiteral(name)
                else:
                    return ExternLiteral(name)
            case Absolute(path):
                return DefinitionLiteral(path)
            case Call() as call:
                return visit_call(call, ctx)
            case Lambda() as lamb:
                return visit_lambda(lamb, ctx)
            case _:
                raise CompileHLIRError(f"unexpected AST node encountered: {expr}")

    def visit_call(call: Call, ctx: LambdaContext) -> ValueLiteral:
        fn = visit_expr(call.fn, ctx)
        arg = visit_expr(call.arg, ctx)
        res = ctx.get_temp_capture_literal()
        param = ctx.get_serialized_call_param(res.id)
        ctx.calls.append(SerializedCall(fn, arg, res.id, param))
        return res

    def visit_lambda(lamb: Lambda, ctx: LambdaContext) -> ValueLiteral:
        scope = list(ctx.scope)
        if lamb.name in scope:
            scope.remove(lamb.name)
        scope.insert(0, lamb.name)

        subctx = LambdaContext(ctx.path, get_lambda_id(ctx.path), scope)

        impl, captures = visit_body_expr(lamb.body, subctx)
        ctx.impls += subctx.impls

        return LambdaLiteral(subctx.id, captures)

    def visit_body_expr(expr: Expr, ctx: LambdaContext) -> Tuple[mlir.Implementation, List[str]]:
        captures: Set[Optional[str | int]] = set()

        result = ctx.get_serialized_call_result(visit_expr(expr, ctx))

        captures.add(result.param)
        visit_lit_captures(result.value, captures)
        capture_lookup = ctx.sort_captures(captures)
        captures.remove(result.param)

        if len(ctx.calls) == 0:
            ctx.impls.append(mlir.ReturnImplementation(
                ImplementationPath(ctx.path, ctx.id, 0),
                ctx.anonymize_captures(capture_lookup),
                visit_lit_convert(result.value, capture_lookup, ctx)
            ))

        first = True
        prev_captures: List[str | int] = cast(List[str | int], capture_lookup[1:])
        for call in reversed(ctx.calls):
            assert all(isinstance(cap, (str, int)) for cap in prev_captures)

            captures.add(call.param)
            visit_lit_captures(call.fn, captures)
            visit_lit_captures(call.arg, captures)
            capture_lookup = ctx.sort_captures(captures)
            captures.remove(call.param)

            path = ImplementationPath(ctx.path, ctx.id, call.res)
            impl_captures = ctx.anonymize_captures(capture_lookup)
            fn = visit_lit_convert(call.fn, capture_lookup, ctx)
            arg = visit_lit_convert(call.arg, capture_lookup, ctx)

            if first:
                ctx.impls.append(mlir.TailCallImplementation(
                    path, impl_captures, fn, arg
                ))
            else:
                next = visit_lit_convert(ContinuationLiteral(call.res + 1, prev_captures), capture_lookup, ctx)
                ctx.impls.append(mlir.ContinueCallImplementation(
                    path, impl_captures, fn, arg, next
                ))

            first = False
            prev_captures = cast(List[str | int], capture_lookup[1:])

        capture_lookup = ctx.sort_captures(captures)
        assert all(isinstance(cap, str) for cap in capture_lookup)

        return ctx.impls[-1], cast(List[str], capture_lookup)

    def visit_lit_captures(lit: ValueLiteral, captures: Set[Optional[str | int]]):
        match lit:
            case ExternLiteral() | DefinitionLiteral():
                pass
            case NamedCaptureLiteral(name):
                captures.add(name)
            case TemporaryCaptureLiteral(id):
                captures.add(id)
            case LambdaLiteral(id, lamb_captures):
                for name in lamb_captures:
                    captures.add(name)
            case _:
                raise CompileHLIRError(f"unexpected AST node encountered: {lit}")

    def visit_lit_convert(lit: ValueLiteral, captures: List[Optional[str | int]], ctx: LambdaContext) -> mlir.ValueLiteral:
        match lit:
            case ExternLiteral(name):
                return mlir.ExternLiteral(name)
            case DefinitionLiteral(path):
                return mlir.DefinitionLiteral(path)
            case NamedCaptureLiteral(name):
                return mlir.CaptureLiteral(captures.index(name))
            case TemporaryCaptureLiteral(id):
                return mlir.CaptureLiteral(captures.index(id))
            case LambdaLiteral(id, lamb_captures):
                return mlir.ImplementationLiteral(
                    ImplementationPath(ctx.path, id, 0),
                    [captures.index(cap) for cap in lamb_captures]
                )
            case ContinuationLiteral(id, cont_captures):
                return mlir.ImplementationLiteral(
                    ImplementationPath(ctx.path, ctx.id, id),
                    [captures.index(cap) for cap in cont_captures]
                )
            case _:
                raise CompileHLIRError(f"unexpected AST node encountered: {lit}")

    return visit_program(prog)
