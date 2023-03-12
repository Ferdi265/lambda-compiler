from typing import *
from ...ast.path import Path
from ...ast import lang_linked as lang
from ...ast import hlir_linked as hlir

SourceFile: TypeAlias = lang.SourceFile | hlir.SourceFile
def crate_order(main_crate: SourceFile, order: Optional[List[SourceFile]] = None) -> List[SourceFile]:
    if order is None:
        order = []

    for crate in order:
        if crate.name == main_crate.name:
            return order

    def visit_file(mod: SourceFile):
        for stmt in mod.prog:
            match stmt:
                case lang.LinkedExternCrate(name, file) | hlir.LinkedExternCrate(name, file):
                    crate_order(file, order)
                case lang.LinkedMod(name, is_public, file):
                    visit_file(file)
                case _:
                    pass

    visit_file(main_crate)
    order.insert(0, main_crate)
    return order

def mod_order(main_mod: SourceFile, order: Optional[List[SourceFile]] = None) -> List[SourceFile]:
    if order is None:
        order = []

    if main_mod in order:
        return order

    for stmt in main_mod.prog:
        match stmt:
            case lang.LinkedMod(name, is_public, file):
                mod_order(file, order)

    order.insert(0, main_mod)
    return order
