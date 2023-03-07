from typing import *

from .parse import *
from .instantiate import *

import string

def parse_mlir(s: str, file: str) -> List[Statement]:
    tokens = tokenize(s)
    cur, curs, line, col = Token.End, "", 1, 1

    inst_table: Dict[Tuple[Path, int], Instance] = {}
    impl_table: Dict[Tuple[Path, int, int], Implementation] = {}

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

    def parse_inst_path(path: Optional[Path] = None) -> Tuple[Path, int]:
        if path is None:
            inst_path = parse_path()
        else:
            inst_path = path

        eat(Token.InstSep)
        inst_id = parse_num()

        return inst_path, inst_id

    def parse_impl_path(path: Optional[Path] = None) -> Tuple[Path, int, int]:
        if path is None:
            impl_path = parse_path()
        else:
            impl_path = path

        eat(Token.ImplSep)
        lambda_id = parse_num()
        eat(Token.ImplSep)
        continuation_id = parse_num()

        return impl_path, lambda_id, continuation_id

    def lookup_inst(path: Optional[Path] = None) -> Instance:
        inst_path, inst_id = parse_inst_path(path)
        if (inst_path, inst_id) not in inst_table:
            err(f"unknown instance {inst_path}%{inst_id}")
        return inst_table[(inst_path, inst_id)]

    def lookup_impl(path: Optional[Path] = None) -> Implementation:
        impl_path, lambda_id, continuation_id = parse_impl_path(path)
        if (impl_path, lambda_id, continuation_id) not in impl_table:
            err(f"unknown impl {impl_path}!{lambda_id}!{continuation_id}")
        return impl_table[(impl_path, lambda_id, continuation_id)]

    def parse_extern_crate() -> ExternCrate:
        eat(Token.Extern)
        eat(Token.Crate)
        name = eat(Token.Ident)
        eat(Token.SemiColon)

        return ExternCrate(name)

    def parse_def() -> InstanceDefinition:
        is_public = False
        if cur == Token.Pub:
            eat()
            is_public = True

        path = parse_path()
        eat(Token.Assign)

        inst = lookup_inst()

        needs_init = False
        if cur == Token.NullCall:
            eat()
            needs_init = True

        eat(Token.SemiColon)
        return InstanceDefinition(path, inst, needs_init, is_public)

    def parse_inst() -> Instance:
        eat(Token.Inst)
        inst_path, inst_id = parse_inst_path()
        eat(Token.Assign)

        impl = lookup_impl()

        captures = []
        eat(Token.CaptureOpen)
        while cur != Token.CaptureClose:
            captures.append(lookup_inst())
        eat(Token.CaptureClose)

        eat(Token.SemiColon)
        inst = Instance(inst_path, inst_id, impl, captures)

        inst_table[(inst_path, inst_id)] = inst
        return inst

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
            inst = lookup_inst(path)
            return InstanceLiteral(inst)
        elif cur == Token.ImplSep:
            impl_path, lambda_id, continuation_id = parse_impl_path(path)

            impl_captures: List[int] = []
            eat(Token.CaptureOpen)
            while cur != Token.CaptureClose:
                eat(Token.CapturePrefix)
                id = parse_num()
                captures.add(id)
                impl_captures.append(id)
            eat(Token.CaptureClose)

            impl = Implementation(impl_path, lambda_id, continuation_id, AnonymousLiteral(0), [], impl_captures, False)
            return ImplementationLiteral(impl)
        else:
            return PathLiteral(PathGlobal(path))


    def parse_impl() -> Implementation:
        eat(Token.Impl)
        impl_path, lambda_id, continuation_id = parse_impl_path()
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
        impl_metadata: Tuple[Path, int, int, ValueLiteral, List[str], List[int], bool] = (
            impl_path, lambda_id, continuation_id, AnonymousLiteral(0), [], list(captures), False
        )
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

        impl_table[(impl_path, lambda_id, continuation_id)] = impl
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
