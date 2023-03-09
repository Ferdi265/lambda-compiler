from .parser import *
from .lang import NumberParser
from ..ast.mlir import *

def parse_mlir(code: str, file: str) -> List[Statement]:
    p = NumberParser(code, file)

    def parse_inst_path(path: Optional[Path] = None) -> InstancePath:
        if path is None:
            inst_path = p.parse_absolute_path()
        else:
            inst_path = path

        p.eat(Token.InstSep)
        inst_id = p.parse_number()

        return InstancePath(inst_path, inst_id)

    def parse_impl_path(path: Optional[Path] = None) -> ImplementationPath:
        if path is None:
            impl_path = p.parse_absolute_path()
        else:
            impl_path = path

        p.eat(Token.ImplSep)
        lambda_id = p.parse_number()
        p.eat(Token.ImplSep)
        continuation_id = p.parse_number()

        return ImplementationPath(impl_path, lambda_id, continuation_id)

    def parse_extern_crate() -> ExternCrate:
        p.eat(Token.Extern)
        p.eat(Token.Crate)
        name = p.eat(Token.Ident)
        p.eat(Token.SemiColon)

        return ExternCrate(name)

    def parse_def() -> Definition:
        is_public = False
        if p.token == Token.Pub:
            p.eat()
            is_public = True

        path = p.parse_absolute_path()
        p.eat(Token.Assign)

        inst = parse_inst_path()

        needs_init = False
        if p.token == Token.NullCall:
            p.eat()
            needs_init = True

        p.eat(Token.SemiColon)
        return Definition(path, inst, needs_init, is_public)

    def parse_inst() -> Instance:
        p.eat(Token.Inst)
        inst = parse_inst_path()
        p.eat(Token.Assign)

        impl = parse_impl_path()

        captures = []
        p.eat(Token.CaptureOpen)
        while p.token != Token.CaptureClose:
            captures.append(parse_inst_path())
        p.eat(Token.CaptureClose)

        p.eat(Token.SemiColon)
        return Instance(inst, impl, captures)

    def parse_capture(captures: OrderedSet[int]) -> int | InstancePath:
        if p.token == Token.CapturePrefix:
            p.eat()
            id = p.parse_number()
            captures.add(id)
            return id
        else:
            return parse_inst_path()

    def parse_value_lit(captures: OrderedSet[int]) -> ValueLiteral:
        if p.token == Token.CapturePrefix:
            p.eat()
            id = p.parse_number()
            captures.add(id)
            return CaptureLiteral(id)

        name = p.eat(Token.Ident)
        if p.token != Token.PathSep:
            return ExternLiteral(name)

        path = p.parse_absolute_path(name)
        if p.token == Token.InstSep:
            inst = parse_inst_path(path)
            return InstanceLiteral(inst)
        elif p.token == Token.ImplSep:
            impl_path = parse_impl_path(path)

            impl_captures: List[int | InstancePath] = []
            p.eat(Token.CaptureOpen)
            while p.token != Token.CaptureClose:
                impl_captures.append(parse_capture(captures))
            p.eat(Token.CaptureClose)

            return ImplementationLiteral(impl_path, impl_captures)
        else:
            return DefinitionLiteral(path)

    def parse_impl() -> Implementation:
        p.eat(Token.Impl)
        impl_path = parse_impl_path()
        p.eat(Token.Assign)

        captures: OrderedSet[int] = OrderedSet()

        a, b, c = parse_value_lit(captures), None, None
        if p.token != Token.SemiColon:
            b = parse_value_lit(captures)
        if p.token != Token.SemiColon:
            p.eat(Token.Arrow)
            c = parse_value_lit(captures)

        captures.remove(0)

        p.eat(Token.SemiColon)
        impl_metadata: Tuple[ImplementationPath, List[int]] = (impl_path, list(captures))
        impl: Implementation
        match (a, b, c):
            case (a, None, None):
                impl = ReturnImplementation(*impl_metadata, a)
            case (a, b, None):
                assert b is not None
                impl = TailCallImplementation(*impl_metadata, a, b)
            case (a, b, c):
                assert b is not None and c is not None
                impl = ContinueCallImplementation(*impl_metadata, a, b, c)

        return impl

    def parse_statement() -> Statement:
        if p.token == Token.Extern:
            return parse_extern_crate()
        elif p.token == Token.Impl:
            return parse_impl()
        elif p.token == Token.Inst:
            return parse_inst()
        else:
            return parse_def()

    def parse_prog() -> List[Statement]:
        statements: List[Statement] = []
        while p.token != Token.End:
            statements.append(parse_statement())

        p.eat(Token.End)
        return statements

    return parse_prog()
