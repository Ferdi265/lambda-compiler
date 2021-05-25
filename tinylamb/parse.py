from typing import *
from enum import Enum, auto
import copy
import re

from .ast import *

class Token(Enum):
    ParenOpen = auto()
    ParenClose = auto()
    Arrow = auto()
    Assign = auto()
    SemiColon = auto()
    Ident = auto()
    End = auto()

patterns: List[Tuple[str, Optional[Token]]] = [
    (" +", None),
    ("=", Token.Assign),
    (";", Token.SemiColon),
    ("\\(", Token.ParenOpen),
    ("\\)", Token.ParenClose),
    ("->", Token.Arrow),
    ("[a-zA-Z_0-9]*", Token.Ident),
]

def tokenize(s: str) -> Generator[Tuple[Token, str], None, None]:
    while len(s) > 0:
        for (p, t) in patterns:
            m = re.match("^" + p, s)
            if m is None:
                continue

            ms = m.group(0)
            s = s[len(ms):]
            if t is not None:
                yield (t, ms)
            break
        else:
            raise ValueError(f"tokenize error at: '{s}'")

class ParseError(Exception):
    pass

def parse(s: str) -> List[Statement]:
    tokens = tokenize(s)
    cur, curs = Token.End, ""

    def drop():
        nonlocal cur, curs
        try:
            cur, curs = next(tokens)
        except StopIteration:
            cur, curs = Token.End, ""

    drop()

    def eat(t: Optional[Token] = None) -> str:
        if t is not None and cur != t:
            err()
        cs = curs
        drop()
        return cs

    def err():
        raise ParseError(f"parse error at ({cur}, '{curs}')")

    def parse_paren() -> Paren:
        chain = Paren(parse_chain())
        eat(Token.ParenClose)
        return chain

    def parse_expr() -> Expr:
        if cur == Token.ParenOpen:
            drop()
            return parse_paren()
        if cur == Token.Ident:
            name = eat()
            if cur == Token.Arrow:
                drop()
                return Lambda(name, parse_chain())
            return Ident(name)
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
        return Assignment(name, value)

    def parse_prog() -> List[Statement]:
        statements = []
        while cur != Token.End:
            statements.append(parse_assignment())

        eat(Token.End)
        return statements

    return parse_prog()
