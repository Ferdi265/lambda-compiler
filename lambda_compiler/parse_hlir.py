from typing import *
from .parse import *

def parse_hlir(s: str, file: str, stub: bool = False) -> List[Statement]:
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

    def parse_path(crate: str) -> Path:
        components = [crate]
        while cur == Token.PathSep:
            eat()
            components.append(eat(Token.Ident))

        return Path(components)

    def parse_paren() -> Paren:
        chain = Paren(parse_chain())
        eat(Token.ParenClose)
        return chain

    def parse_expr() -> Expr:
        expr: Expr
        if cur == Token.Ellipsis and stub:
            eat()
            expr = EllipsisExpr()
        elif cur == Token.ParenOpen:
            drop()
            expr = parse_paren()
        elif cur == Token.Ident:
            name = eat()
            if cur == Token.PathSep:
                expr = PathExpr(parse_path(name))
            elif cur == Token.Arrow:
                drop()
                expr = Lambda(name, parse_chain())
            else:
                expr = Ident(name)
        else:
            err()

        if stub:
            expr = EllipsisExpr()

        return expr

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
        path = parse_path(name)

        eat(Token.Assign)

        if cur == Token.Use:
            if not is_public:
                err("alias definitions must be public")
            if is_impure:
                err("alias definitions cannot be impure")

            eat()
            alias_name = eat(Token.Ident)
            alias_path = parse_path(name)
            eat(Token.SemiColon)
            return PathAlias(path, alias_path, is_public)
        else:
            value = parse_chain()
            eat(Token.SemiColon)
            return PathAssignment(path, value, is_public, is_impure)

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

        return parse_assignment(is_public)

    def parse_prog() -> List[Statement]:
        statements: List[Statement] = []
        while cur != Token.End:
            statements.append(parse_statement())

        eat(Token.End)
        return statements

    return parse_prog()

