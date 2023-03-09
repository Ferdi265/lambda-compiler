from typing import *
from .parse import *

def parse_lang(s: str, file: str) -> List[Statement]:
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

    def err() -> NoReturn:
        raise ParseError(f"parse error in file {file} at line {line} col {col}: ({cur}, '{curs}')")

    def is_number() -> bool:
        try:
            int(curs)
            return True
        except ValueError:
            return False

    def parse_path_component(first: bool, allow_super: bool) -> str:
        if cur == Token.Ident:
            return eat()
        elif first and cur == Token.Crate:
            return eat()
        elif first and cur == Token.Self:
            return eat()
        elif allow_super and cur == Token.Super:
            return eat()
        else:
            err()

    def parse_path(base: Optional[str] = None) -> Path:
        first, allow_super = True, True
        components = [parse_path_component(first, allow_super) if base is None else base]
        while cur == Token.PathSep:
            eat()

            first, allow_super = False, allow_super and components[-1] == "super"
            components.append(parse_path_component(first, allow_super))

        return Path(components)

    def parse_path_all(base: Optional[str] = None) -> Tuple[Path, bool]:
        first, allow_super = True, True
        components = [parse_path_component(first, allow_super) if base is None else base]
        is_all = False
        while cur == Token.PathSep:
            eat()
            if cur == Token.All:
                eat()
                is_all = True
                break

            first, allow_super = False, allow_super and components[-1] == "super"
            components.append(parse_path_component(first, allow_super))

        return Path(components), is_all

    def parse_paren() -> Paren:
        chain = Paren(parse_chain())
        eat(Token.ParenClose)
        return chain

    def parse_string() -> String:
        s = eat(Token.String)
        s = ast.literal_eval(s)
        return String(s)

    def parse_num() -> Number:
        s = eat(Token.Ident)
        return Number(int(s))

    def parse_macro() -> Macro:
        eat(Token.MacroMarker)

        if cur == Token.String:
            return parse_string()
        elif cur == Token.Ident and is_number():
            return parse_num()
        err()

    def parse_expr() -> Expr:
        if cur == Token.ParenOpen:
            drop()
            return parse_paren()
        elif cur == Token.Ident:
            name = eat()
            if cur == Token.PathSep:
                return PathExpr(parse_path(name))
            elif cur == Token.Arrow:
                drop()
                return Lambda(name, parse_chain())
            return Ident(name)
        elif cur == Token.MacroMarker:
            return parse_macro()
        else:
            # must be a path beginning with crate, super, or self
            return PathExpr(parse_path())
        err()

    def parse_chain() -> Expr:
        prev = parse_expr()
        while cur != Token.ParenClose and cur != Token.SemiColon:
            expr = parse_expr()
            prev = Call(prev, expr)
        return prev

    def parse_assignment(is_public: bool) -> Assignment:
        is_impure = False
        if cur == Token.Impure:
            eat()
            is_impure = True

        name = eat(Token.Ident)

        eat(Token.Assign)
        value = parse_chain()
        eat(Token.SemiColon)

        return NameAssignment(name, value, is_public, is_impure)

    def parse_import(is_public: bool) -> Union[ImportAll, Import]:
        eat(Token.Use)

        path, is_all = parse_path_all()

        if is_all:
            eat(Token.SemiColon)
            return ImportAll(path, is_public)
        else:
            name: str
            if cur == Token.As:
                eat()
                name = eat(Token.Ident)
            else:
                name = path.components[-1]

            eat(Token.SemiColon)
            return Import(path, name, is_public)

    def parse_mod(is_public: bool) -> Mod:
        eat(Token.Mod)
        name = eat(Token.Ident)

        eat(Token.SemiColon)
        return Mod(name, is_public)

    def parse_extern_crate() -> ExternCrate:
        eat(Token.Crate)
        name = eat(Token.Ident)
        eat(Token.SemiColon)

        return ExternCrate(name)

    def parse_extern_impure() -> Extern:
        eat(Token.Impure)
        name = eat(Token.Ident)
        eat(Token.SemiColon)

        return Extern(name)

    def parse_extern() -> Statement:
        eat(Token.Extern)

        if cur == Token.Crate:
            return parse_extern_crate()
        elif cur == Token.Impure:
            return parse_extern_impure()
        else:
            err()

    def parse_statement() -> Statement:
        if cur == Token.Extern:
            return parse_extern()

        is_public = False
        if cur == Token.Pub:
            eat()
            is_public = True

        if cur == Token.Use:
            return parse_import(is_public)
        elif cur == Token.Mod:
            return parse_mod(is_public)
        else:
            return parse_assignment(is_public)

    def parse_prog() -> List[Statement]:
        statements: List[Statement] = []
        while cur != Token.End:
            statements.append(parse_statement())

        eat(Token.End)
        return statements

    return parse_prog()

