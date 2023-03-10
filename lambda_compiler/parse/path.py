from .parser import Parser, Token
from ..ast.path import *

class PathParser(Parser):
    def parse_relative_path_component(self, first: bool, allow_super: bool) -> str:
        if self.token == Token.Ident:
            return self.eat()
        elif first and self.token == Token.Crate:
            return self.eat()
        elif first and self.token == Token.Self:
            return self.eat()
        elif allow_super and self.token == Token.Super:
            return self.eat()
        else:
            self.err()

    def parse_relative_path(self, base: Optional[str] = None) -> Path:
        first, allow_super = True, True
        components = [self.parse_relative_path_component(first, allow_super) if base is None else base]
        while self.token == Token.PathSep:
            self.eat()

            first, allow_super = False, allow_super and components[-1] == "super"
            components.append(self.parse_relative_path_component(first, allow_super))

        return Path(components)

    def parse_relative_path_all(self, base: Optional[str] = None) -> Tuple[Path, bool]:
        first, allow_super = True, True
        components = [self.parse_relative_path_component(first, allow_super) if base is None else base]
        is_all = False
        while self.token == Token.PathSep:
            self.eat()
            if self.token == Token.All:
                self.eat()
                is_all = True
                break

            first, allow_super = False, allow_super and components[-1] == "super"
            components.append(self.parse_relative_path_component(first, allow_super))

        return Path(components), is_all

    def parse_absolute_path(self, base: Optional[str] = None) -> Path:
        components = [self.eat(Token.Ident) if base is None else base]
        while self.token == Token.PathSep:
            self.eat()
            components.append(self.eat(Token.Ident))

        return Path(components)

def parse_path(path_str: str) -> Path:
    p = PathParser(path_str, "<internal>")

    path = p.parse_relative_path()
    p.eat(Token.End)
    return path
