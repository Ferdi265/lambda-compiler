from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import *
import re

class Token(Enum):
    Assign = auto()
    SemiColon = auto()
    ParenOpen = auto()
    ParenClose = auto()
    Arrow = auto()
    All = auto()
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
    Super = auto()
    Self = auto()
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
    (r"\*", Token.All),
    ("::", Token.PathSep),
    ("!", Token.ImplSep),
    ("%", Token.InstSep),
    (r"\$\$", Token.NullCall),
    (r"\$", Token.CapturePrefix),
    (r"\[", Token.CaptureOpen),
    (r"\]", Token.CaptureClose),
    (r"\.\.\.", Token.Ellipsis),
    ("pub(?=[^a-zA-Z0-9])", Token.Pub),
    ("impure(?=[^a-zA-Z0-9])", Token.Impure),
    ("mod(?=[^a-zA-Z0-9])", Token.Mod),
    ("use(?=[^a-zA-Z0-9])", Token.Use),
    ("as(?=[^a-zA-Z0-9])", Token.As),
    ("extern(?=[^a-zA-Z0-9])", Token.Extern),
    ("crate(?=[^a-zA-Z0-9])", Token.Crate),
    ("super(?=[^a-zA-Z0-9])", Token.Super),
    ("self(?=[^a-zA-Z0-9])", Token.Self),
    ("impl(?=[^a-zA-Z0-9])", Token.Impl),
    ("inst(?=[^a-zA-Z0-9])", Token.Inst),
    (r'"([^"\\]|\\[^\n])*"', Token.String),
    ("[a-zA-Z_0-9]+", Token.Ident),
]

class Tokenized(NamedTuple):
    token: Token
    text: str
    line: int
    col: int

class TokenizeError(Exception):
    pass

class ParseError(Exception):
    pass

class Parser:
    rest: str
    file: str
    tokens: Generator[Tokenized, None, None]

    token: Token = Token.End
    text: str = ""
    line: int = 1
    col: int = 1

    def __init__(self, rest: str, file: str):
        self.rest = rest
        self.file = file
        self.tokens = self.tokenize()
        self.drop()

    def tokenize(self) -> Generator[Tokenized, None, None]:
        line = 1
        col = 1
        while len(self.rest) > 0:
            for (p, t) in patterns:
                m = re.match("^" + p, self.rest)
                if m is None:
                    continue

                ms = m.group(0)
                self.rest = self.rest[len(ms):]
                if t is not None:
                    yield Tokenized(t, ms, line, col)

                col = col + len(ms) if "\n" not in ms else 1 + len(ms.rsplit("\n", 1)[1])
                line += sum(c == "\n" for c in ms)
                break
            else:
                raise TokenizeError(f"tokenize error in file {self.file} at line {line} col {col}: '{self.rest}'")

    def drop(self):
        try:
            self.token, self.text, self.line, self.col = next(self.tokens)
        except StopIteration:
            self.token, self.text = Token.End, ""

    def eat(self, t: Optional[Token] = None) -> str:
        if t is not None and self.token != t:
            self.err()
        cs = self.text
        self.drop()
        return cs

    def err(self, s: Optional[str] = None) -> NoReturn:
        msg = f": {s}" if s is not None else ""
        raise ParseError(f"parse error in file {self.file} at line {self.line} col {self.col}: ({self.token}, '{self.text}'){msg}")
