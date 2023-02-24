from typing import *
from enum import Enum, auto
import ast
import re

from .ast import *

class Token(Enum):
    Assign = auto()
    SemiColon = auto()
    ParenOpen = auto()
    ParenClose = auto()
    Arrow = auto()
    PathSep = auto()
    ImplSep = auto()
    InstSep = auto()
    NullCall = auto()
    CapturePrefix = auto()
    CaptureOpen = auto()
    CaptureClose = auto()
    Ellipsis = auto()
    Pub = auto()
    Impure = auto()
    Mod = auto()
    Use = auto()
    As = auto()
    Extern = auto()
    Crate = auto()
    Impl = auto()
    Inst = auto()
    String = auto()
    Ident = auto()
    End = auto()

    MacroMarker = ImplSep

patterns: List[Tuple[str, Optional[Token]]] = [
    ("( |\n)+", None),
    ("#[^\n]*", None),
    ("=", Token.Assign),
    (";", Token.SemiColon),
    (r"\(", Token.ParenOpen),
    (r"\)", Token.ParenClose),
    ("->", Token.Arrow),
    ("::", Token.PathSep),
    ("!", Token.ImplSep),
    ("%", Token.InstSep),
    (r"\$\$", Token.NullCall),
    (r"\$", Token.CapturePrefix),
    (r"\[", Token.CaptureOpen),
    (r"\]", Token.CaptureClose),
    (r"\.\.\.", Token.Ellipsis),
    ("pub", Token.Pub),
    ("impure", Token.Impure),
    ("mod", Token.Mod),
    ("use", Token.Use),
    ("as", Token.As),
    ("extern", Token.Extern),
    ("crate", Token.Crate),
    ("impl", Token.Impl),
    ("inst", Token.Inst),
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
