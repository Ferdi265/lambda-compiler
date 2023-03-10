from typing import *
from .parser import Token
from .path import PathParser
from ..ast.lang import *
import ast as pyast

class NumberParser(PathParser):
    def is_number(self) -> bool:
        try:
            int(self.text)
            return True
        except ValueError:
            return False

    def parse_number(self) -> int:
        s = self.eat(Token.Ident)
        return int(s)

def parse_lang(code: str, file: str) -> List[Statement]:
    p = NumberParser(code, file)

    def parse_paren() -> Paren:
        chain = Paren(parse_chain())
        p.eat(Token.ParenClose)
        return chain

    def parse_string() -> String:
        s = p.eat(Token.String)
        s = pyast.literal_eval(s)
        return String(s)

    def parse_num() -> Number:
        return Number(p.parse_number())

    def parse_macro() -> Macro:
        p.eat(Token.MacroMarker)

        if p.token == Token.String:
            return parse_string()
        elif p.token == Token.Ident and p.is_number():
            return parse_num()
        p.err()

    def parse_expr() -> Expr:
        if p.token == Token.ParenOpen:
            p.drop()
            return parse_paren()
        elif p.token == Token.Ident:
            name = p.eat()
            if p.token == Token.PathSep:
                return Relative(p.parse_relative_path(name))
            elif p.token == Token.Arrow:
                p.drop()
                return Lambda(name, parse_chain())
            return Ident(name)
        elif p.token == Token.MacroMarker:
            return parse_macro()
        else:
            # must be a path beginning with crate, super, or self
            return Relative(p.parse_relative_path())
        p.err()

    def parse_chain() -> Expr:
        prev = parse_expr()
        while p.token != Token.ParenClose and p.token != Token.SemiColon:
            expr = parse_expr()
            prev = Call(prev, expr)
        return prev

    def parse_assignment(is_public: bool) -> Assignment:
        is_impure = False
        if p.token == Token.Impure:
            p.eat()
            is_impure = True

        name = p.eat(Token.Ident)

        p.eat(Token.Assign)
        value = parse_chain()
        p.eat(Token.SemiColon)

        return Assignment(name, value, is_public, is_impure)

    def parse_import(is_public: bool) -> ImportAll | Import:
        p.eat(Token.Use)

        path, is_all = p.parse_relative_path_all()

        if is_all:
            p.eat(Token.SemiColon)
            return ImportAll(path, is_public)
        else:
            name: str
            if p.token == Token.As:
                p.eat()
                name = p.eat(Token.Ident)
            else:
                name = path.components[-1]

            p.eat(Token.SemiColon)
            return Import(path, name, is_public)

    def parse_mod(is_public: bool) -> Mod:
        p.eat(Token.Mod)
        name = p.eat(Token.Ident)

        p.eat(Token.SemiColon)
        return Mod(name, is_public)

    def parse_extern_crate() -> ExternCrate:
        p.eat(Token.Crate)
        name = p.eat(Token.Ident)
        p.eat(Token.SemiColon)

        return ExternCrate(name)

    def parse_extern_impure() -> Extern:
        p.eat(Token.Impure)
        name = p.eat(Token.Ident)
        p.eat(Token.SemiColon)

        return Extern(name)

    def parse_extern() -> Statement:
        p.eat(Token.Extern)

        if p.token == Token.Crate:
            return parse_extern_crate()
        elif p.token == Token.Impure:
            return parse_extern_impure()
        else:
            p.err()

    def parse_statement() -> Statement:
        if p.token == Token.Extern:
            return parse_extern()

        is_public = False
        if p.token == Token.Pub:
            p.eat()
            is_public = True

        if p.token == Token.Use:
            return parse_import(is_public)
        elif p.token == Token.Mod:
            return parse_mod(is_public)
        else:
            return parse_assignment(is_public)

    def parse_prog() -> List[Statement]:
        statements: List[Statement] = []
        while p.token != Token.End:
            statements.append(parse_statement())

        p.eat(Token.End)
        return statements

    return parse_prog()
