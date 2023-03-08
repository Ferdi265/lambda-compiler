from typing import *

from .parse import *
from .instantiate import *

import string

@dataclass(frozen=True)
class InstancePath:
    path: Path
    inst_id: int

@dataclass(frozen=True)
class ImplementationPath:
    path: Path
    lambda_id: int
    continuation_id: int

@dataclass
class MInstanceDefinition(Statement):
    path: Path
    inst: InstancePath
    needs_init: bool
    is_public: bool

@dataclass
class MInstance(Statement):
    path: InstancePath
    impl: ImplementationPath
    captures: List[InstancePath]

@dataclass
class MImplementation(Statement):
    path: ImplementationPath
    captures: List[int]

@dataclass
class MReturnImplementation(MImplementation):
    value: ValueLiteral

@dataclass
class MTailCallImplementation(MImplementation):
    fn: ValueLiteral
    arg: ValueLiteral

@dataclass
class MContinueCallImplementation(MImplementation):
    fn: ValueLiteral
    arg: ValueLiteral
    next: ValueLiteral

@dataclass
class MInstanceLiteral(ValueLiteral):
    inst: InstancePath

@dataclass
class MImplementationLiteral(ValueLiteral):
    impl: MImplementation

def parse_mlir(s: str, file: str) -> List[Statement]:
    tokens = tokenize(s)
    cur, curs, line, col = Token.End, "", 1, 1

    def drop():
        nonlocal cur, curs, line, col
        try:
            cur, curs, line, col = next(tokens)
        except StopIteration:
            cur, curs = Token.End, ""

    drop()

    def eat(t: Optional[Token] = None) -> str:
        if t is not None and cur != t:
            err()
        cs = curs
        drop()
        return cs

    def err(s: Optional[str] = None) -> NoReturn:
        msg = f": {s}" if s is not None else ""
        raise ParseError(f"parse error in file {file} at line {line} col {col}: ({cur}, '{curs}'){msg}")

    def parse_path(base: Optional[str] = None) -> Path:
        components = [eat(Token.Ident) if base is None else base]
        while cur == Token.PathSep:
            eat()
            components.append(eat(Token.Ident))

        return Path(components)

    def parse_num() -> int:
        num_str = eat(Token.Ident)

        try:
            return int(num_str)
        except ValueError:
            err(f"invalid number {num_str!r}")

    def parse_inst_path(path: Optional[Path] = None) -> InstancePath:
        if path is None:
            inst_path = parse_path()
        else:
            inst_path = path

        eat(Token.InstSep)
        inst_id = parse_num()

        return InstancePath(inst_path, inst_id)

    def parse_impl_path(path: Optional[Path] = None) -> ImplementationPath:
        if path is None:
            impl_path = parse_path()
        else:
            impl_path = path

        eat(Token.ImplSep)
        lambda_id = parse_num()
        eat(Token.ImplSep)
        continuation_id = parse_num()

        return ImplementationPath(impl_path, lambda_id, continuation_id)

    def parse_extern_crate() -> ExternCrate:
        eat(Token.Extern)
        eat(Token.Crate)
        name = eat(Token.Ident)
        eat(Token.SemiColon)

        return ExternCrate(name)

    def parse_def() -> MInstanceDefinition:
        is_public = False
        if cur == Token.Pub:
            eat()
            is_public = True

        path = parse_path()
        eat(Token.Assign)

        inst = parse_inst_path()

        needs_init = False
        if cur == Token.NullCall:
            eat()
            needs_init = True

        eat(Token.SemiColon)
        return MInstanceDefinition(path, inst, needs_init, is_public)

    def parse_inst() -> MInstance:
        eat(Token.Inst)
        inst = parse_inst_path()
        eat(Token.Assign)

        impl = parse_impl_path()

        captures = []
        eat(Token.CaptureOpen)
        while cur != Token.CaptureClose:
            captures.append(parse_inst_path())
        eat(Token.CaptureClose)

        eat(Token.SemiColon)
        return MInstance(inst, impl, captures)

    def parse_value_lit(captures: OrderedSet[int]) -> ValueLiteral:
        if cur == Token.CapturePrefix:
            eat()
            id = parse_num()
            captures.add(id)
            return AnonymousLiteral(id)

        name = eat(Token.Ident)
        if cur != Token.PathSep:
            return IdentLiteral(ExternGlobal(name))

        path = parse_path(name)
        if cur == Token.InstSep:
            inst = parse_inst_path(path)
            return MInstanceLiteral(inst)
        elif cur == Token.ImplSep:
            impl_path = parse_impl_path(path)

            impl_captures: List[int] = []
            eat(Token.CaptureOpen)
            while cur != Token.CaptureClose:
                eat(Token.CapturePrefix)
                id = parse_num()
                captures.add(id)
                impl_captures.append(id)
            eat(Token.CaptureClose)

            impl = MImplementation(impl_path, impl_captures)
            return MImplementationLiteral(impl)
        else:
            return PathLiteral(PathGlobal(path))

    def parse_impl() -> MImplementation:
        eat(Token.Impl)
        impl_path = parse_impl_path()
        eat(Token.Assign)

        captures: OrderedSet[int] = OrderedSet()

        a, b, c = parse_value_lit(captures), None, None
        if cur != Token.SemiColon:
            b = parse_value_lit(captures)
        if cur != Token.SemiColon:
            eat(Token.Arrow)
            c = parse_value_lit(captures)

        captures.remove(0)

        eat(Token.SemiColon)
        impl_metadata: Tuple[ImplementationPath, List[int]] = (impl_path, list(captures))
        impl: MImplementation
        match (a, b, c):
            case (a, None, None):
                impl = MReturnImplementation(*impl_metadata, a)
            case (a, b, None):
                assert b is not None
                impl = MTailCallImplementation(*impl_metadata, a, b)
            case (a, b, c):
                assert b is not None and c is not None
                impl = MContinueCallImplementation(*impl_metadata, a, b, c)

        return impl

    def parse_statement() -> Statement:
        if cur == Token.Extern:
            return parse_extern_crate()
        elif cur == Token.Impl:
            return parse_impl()
        elif cur == Token.Inst:
            return parse_inst()
        else:
            return parse_def()

    def parse_prog() -> List[Statement]:
        statements: List[Statement] = []
        while cur != Token.End:
            statements.append(parse_statement())

        eat(Token.End)
        return statements

    return parse_prog()
