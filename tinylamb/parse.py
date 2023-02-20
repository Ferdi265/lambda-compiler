from typing import *
from enum import Enum, auto
import ast
import re

from .ast import *

class Token(Enum):
    ParenOpen = auto()
    ParenClose = auto()
    Arrow = auto()
    Assign = auto()
    SemiColon = auto()
    Ident = auto()
    End = auto(),
    PathSep = auto()
    Use = auto()
    As = auto(),
    Extern = auto()
    Crate = auto()
    String = auto()

patterns: List[Tuple[str, Optional[Token]]] = [
    ("( |\n)+", None),
    ("=", Token.Assign),
    (";", Token.SemiColon),
    ("\\(", Token.ParenOpen),
    ("\\)", Token.ParenClose),
    ("->", Token.Arrow),
    ("::", Token.PathSep),
    ("use", Token.Use),
    ("as", Token.As),
    ("extern", Token.Extern),
    ("crate", Token.Crate),
    (r'"([^"\\]|\\[^\n])*"', Token.String),
    ("[a-zA-Z_0-9]+", Token.Ident),
]

class TokenizeError(Exception):
    pass

def tokenize(s: str) -> Generator[Tuple[Token, str, int, int], None, None]:
    line = 1
    col = 1
    while len(s) > 0:
        for (p, t) in patterns:
            m = re.match("^" + p, s)
            if m is None:
                continue

            ms = m.group(0)
            s = s[len(ms):]
            if t is not None:
                yield (t, ms, line, col)

            col = col + len(ms) if "\n" not in ms else 1 + len(ms.rsplit("\n", 1)[1])
            line += sum(c == "\n" for c in ms)
            break
        else:
            raise TokenizeError(f"tokenize error at line {line} col {col}: '{s}'")

class ParseError(Exception):
    pass

def parse(s: str) -> List[Statement]:
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

    def build_call_chain(rest: List[Expr]) -> Expr:
        rest, chain = rest[:-1], rest[-1]
        for expr in reversed(rest):
            chain = Call(expr, chain)
        return chain

    def build_number(n: int) -> Expr:
        digit_globals = [PathExpr(Path(("std", str(digit)))) for digit in str(n)]
        dec_global = PathExpr(Path(("std", f"dec{len(digit_globals)}")))

        if len(digit_globals) == 1:
            return digit_globals[0]

        return Paren(build_call_chain(cast(List[Expr], [dec_global] + digit_globals)))

    def parse_string() -> Expr:
        s = eat(Token.String)
        s = ast.literal_eval(s)

        char_exprs = [build_number(ord(c)) for c in s]
        len_expr = build_number(len(char_exprs))

        list_n_global = PathExpr(Path(("std", "list_n")))
        return Paren(build_call_chain(cast(List[Expr], [list_n_global, len_expr] + char_exprs)))

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
        path: Optional[Path] = None

        name = eat(Token.Ident)
        if cur == Token.PathSep:
            path = parse_path(name)

        eat(Token.Assign)
        value = parse_chain()
        eat(Token.SemiColon)

        if path is None:
            return NameAssignment(name, value)
        else:
            return PathAssignment(path, value)

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

def parse_path(s: str) -> Path:
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

    name = eat(Token.Ident)
    path = parse_path(name)
    eat(Token.End)

    return path
