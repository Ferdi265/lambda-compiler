from .parser import *
from .lang import NumberParser
from ..ast.hlir import *

def parse_hlir(code: str, file: str, stub: bool = False) -> List[Statement]:
    p = NumberParser(code, file)

    def parse_paren() -> Paren:
        chain = Paren(parse_chain())
        p.eat(Token.ParenClose)
        return chain

    def parse_expr() -> Expr:
        expr: Expr
        if p.token == Token.Ellipsis and stub:
            p.eat()
            expr = Ellipsis()
        elif p.token == Token.ParenOpen:
            p.drop()
            expr = parse_paren()
        elif p.token == Token.Ident:
            name = p.eat()
            if p.token == Token.PathSep:
                expr = Absolute(p.parse_absolute_path(name))
            elif p.token == Token.Arrow:
                p.drop()
                expr = Lambda(name, parse_chain())
            else:
                expr = Ident(name)
        else:
            p.err()

        if stub:
            expr = Ellipsis()

        return expr

    def parse_chain() -> Expr:
        prev = parse_expr()
        while p.token != Token.ParenClose and p.token != Token.SemiColon:
            expr = parse_expr()
            prev = Call(prev, expr)
        return prev

    def parse_assignment(is_public: bool) -> Alias | Assignment:
        is_impure = False
        if p.token == Token.Impure:
            p.eat()
            is_impure = True

        name = p.eat(Token.Ident)
        path = p.parse_absolute_path(name)

        p.eat(Token.Assign)

        if p.token == Token.Use:
            if not is_public:
                p.err("alias definitions must be public")
            if is_impure:
                p.err("alias definitions cannot be impure")

            p.eat()
            alias_name = p.eat(Token.Ident)
            alias_path = p.parse_absolute_path(name)
            p.eat(Token.SemiColon)
            return Alias(path, alias_path, is_public)
        else:
            value = parse_chain()
            p.eat(Token.SemiColon)
            return Assignment(path, value, is_public, is_impure)

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

        return parse_assignment(is_public)

    def parse_prog() -> List[Statement]:
        statements: List[Statement] = []
        while p.token != Token.End:
            statements.append(parse_statement())

        p.eat(Token.End)
        return statements

    return parse_prog()
