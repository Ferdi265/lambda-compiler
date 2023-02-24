from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from copy import copy

from .ast import *
from .parse import *

def build_call_chain(rest: List[Expr]) -> Expr:
    chain, rest = rest[0], rest[1:]
    for expr in rest:
        chain = Call(chain, expr)
    return chain

def demacro_string(string: String) -> Expr:
    """
    convert string literals into calls to std::list_n and std::dec2/3
    """

    list_n_path = lambda length: parse_path("std::list_n")

    s = string.content.encode()

    char_exprs = [demacro_number(Number(byte)) for byte in s]
    len_expr = demacro_number(Number(len(char_exprs)))

    list_n = PathExpr(list_n_path(len(char_exprs)))
    return Paren(build_call_chain(cast(List[Expr], [list_n, len_expr] + char_exprs)))

def demacro_number(number: Number) -> Expr:
    """
    convert number literals into calls to std::dec2/3
    """

    digit_path  = lambda digit: parse_path(f"std::{digit}")
    dec_path    = lambda digits: parse_path(f"std::dec{digits}")

    n = number.value

    digits = [PathExpr(digit_path(digit)) for digit in str(n)]
    dec = PathExpr(dec_path(len(digits)))

    if len(digits) == 1:
        return digits[0]

    return Paren(build_call_chain(cast(List[Expr], [dec] + digits)))

class DemacroError(Exception):
    pass

def demacro(prog: List[Statement]) -> List[Statement]:
    def visit_program(prog: List[Statement]) -> List[Statement]:
        return [visit_statement(stmt) for stmt in prog]

    def visit_statement(stmt: Statement) -> Statement:
        match stmt:
            case NameAssignment(name, value, is_public, is_impure) as ass:
                return NameAssignment(name, visit_expr(value), is_public, is_impure)

        return stmt

    def visit_expr(expr: Expr) -> Expr:
        match expr:
            case Paren(inner):
                return Paren(visit_expr(inner))
            case Call(fn, arg):
                return Call(visit_expr(fn), visit_expr(arg))
            case Lambda(args, body) as lamb:
                return Lambda(args, visit_expr(body))
            case Macro() as macro:
                return visit_macro(macro)

        return expr

    def visit_macro(macro: Macro) -> Expr:
        match macro:
            case String() as string:
                return demacro_string(string)
            case Number() as number:
                return demacro_number(number)
            case _:
                raise DemacroError(f"unexpected AST node encountered: {macro}")

    return visit_program(prog)
