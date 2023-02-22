from typing import *
from .parse import *

def parse_lang(s: str) -> List[Statement]:
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
        raise ParseError(f"parse error at line {line} col {col}: ({cur}, '{curs}')")

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

    def parse_string() -> String:
        s = eat(Token.String)
        s = ast.literal_eval(s)
        return String(s)

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
        elif cur == Token.String:
            return parse_string()
        err()

    def parse_chain() -> Expr:
        prev = parse_expr()
        while cur != Token.ParenClose and cur != Token.SemiColon:
            expr = parse_expr()
            prev = Call(prev, expr)
        return prev

    def parse_assignment() -> Assignment:
        name = eat(Token.Ident)

        eat(Token.Assign)
        value = parse_chain()
        eat(Token.SemiColon)

        return NameAssignment(name, value)

    def parse_import() -> Import:
        eat(Token.Use)

        base = eat(Token.Ident)
        path = parse_path(base)

        name: Optional[str] = None
        if cur == Token.As:
            eat()
            name = eat(Token.Ident)

        eat(Token.SemiColon)
        return Import(path, name)

    def parse_extern() -> Statement:
        eat(Token.Extern)

        stmt: Statement
        if cur == Token.Crate:
            eat()
            name = eat(Token.Ident)
            stmt = ExternCrate(name)
        elif cur == Token.Ident:
            name = eat()
            stmt = Extern(name)
        else:
            err()

        eat(Token.SemiColon)
        return stmt

    def parse_statement() -> Statement:
        if cur == Token.Use:
            return parse_import()
        elif cur == Token.Extern:
            return parse_extern()
        else:
            return parse_assignment()

    def parse_prog() -> List[Statement]:
        statements: List[Statement] = []
        while cur != Token.End:
            statements.append(parse_statement())

        eat(Token.End)
        return statements

    return parse_prog()

