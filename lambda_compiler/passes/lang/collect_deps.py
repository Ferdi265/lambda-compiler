from __future__ import annotations
from typing import *
from dataclasses import dataclass
from ...ast.path import Path
from ...ast import lang_linked as lang
from ...ast import hlir_linked as hlir
from ...parse.lang import parse_lang
from ...parse.hlir import parse_hlir
import os.path

class CollectCrateError(Exception):
    pass

def load_initial_crate(file_path: str) -> lang.LinkedExternCrate:
    found = False
    file_name = os.path.basename(file_path)
    dir_path = os.path.dirname(file_path)
    dir_name = os.path.basename(dir_path)

    if not found:
        crate_name = dir_name
        crate_dir = dir_path
        crate_src = file_path
        owns_dir = True
        if os.path.isfile(crate_src) and file_name == "mod.lambda":
            found = True

    if not found:
        crate_name = file_name
        crate_dir = file_path
        crate_src = os.path.join(crate_dir, "mod.lambda")
        owns_dir = True
        if os.path.isfile(crate_src):
            found = True

    if not found:
        crate_name = file_name.split(".", 1)[0]
        crate_dir = dir_path
        crate_src = file_path
        owns_dir = False
        if os.path.isfile(crate_src) and crate_name != "mod":
            found = True

    if not found:
        raise CollectCrateError(f"could not determine crate name and dir from path {file_path}")

    with open(crate_src, "r") as f:
        code = f.read()
        prog = parse_lang(code, crate_src)

    file = lang.SourceFile(crate_name, crate_dir, crate_src, owns_dir, prog)
    return lang.LinkedExternCrate(crate_name, file)

def load_crate(crate: str, crate_path: List[str], blacklist_crates: Set[str], allow_hlir: bool = True, allow_lang: bool = True) -> lang.LinkedExternCrate:
    if crate in blacklist_crates:
        raise CollectCrateError(f"cyclical dependency on crate '{crate}'")

    for dir in crate_path:
        crate_src = os.path.join(dir, f"{crate}.hlis")
        is_hlir = True
        owns_dir = False
        if allow_hlir and os.path.isfile(crate_src):
            break

        crate_src = os.path.join(dir, f"{crate}.hlir")
        is_hlir = True
        owns_dir = False
        if allow_hlir and os.path.isfile(crate_src):
            break

        crate_src = os.path.join(dir, f"{crate}.lambda")
        is_hlir = False
        owns_dir = False
        if allow_lang and os.path.isfile(crate_src):
            break

        crate_src = os.path.join(dir, f"{crate}/mod.lambda")
        is_hlir = False
        owns_dir = True
        if allow_lang and os.path.isfile(crate_src):
            break
    else:
        raise CollectCrateError(f"did not find crate '{crate}'")

    crate_dir = os.path.dirname(crate_src)

    file: lang.SourceFile | hlir.SourceFile
    with open(crate_src, "r") as f:
        code = f.read()
        if is_hlir:
            hlir_prog = parse_hlir(code, crate_src, stub=True)
            file = hlir.SourceFile(crate, crate_dir, crate_src, owns_dir, hlir_prog)
        else:
            lang_prog = parse_lang(code, crate_src)
            file = lang.SourceFile(crate, crate_dir, crate_src, owns_dir, lang_prog)

    return lang.LinkedExternCrate(crate, file)

def load_mod(path: Path, mod: lang.SourceFile, name: str, is_public: bool) -> lang.LinkedMod:
    found = False

    if not found and mod.owns_dir:
        mod_dir = mod.dir
        mod_src = os.path.join(mod_dir, f"{name}.lambda")
        owns_dir = False
        if os.path.isfile(mod_src):
            found = True

    if not found and mod.owns_dir:
        mod_dir = os.path.join(mod.dir, name)
        mod_src = os.path.join(mod_dir, "mod.lambda")
        owns_dir = True
        if os.path.isfile(mod_src):
            found = True

    if not found and not mod.owns_dir:
        mod_dir = os.path.join(mod.dir, mod.name)
        mod_src = os.path.join(mod_dir, f"{name}.lambda")
        owns_dir = False
        if os.path.isfile(mod_src):
            found = True

    if not found and not mod.owns_dir:
        mod_dir = os.path.join(mod.dir, mod.name, name)
        mod_src = os.path.join(mod_dir, "mod.lambda")
        owns_dir = True
        if os.path.isfile(mod_src):
            found = True

    if not found:
        raise CollectCrateError(f"did not find module '{path / name}'")

    with open(mod_src, "r") as f:
        code = f.read()
        prog = parse_lang(code, mod_src)

    file = lang.SourceFile(name, mod_dir, mod_src, owns_dir, prog)
    return lang.LinkedMod(name, is_public, file)

@dataclass
class CollectCrateContext:
    cur: lang.SourceFile | hlir.SourceFile
    path: Path

    blacklist_crates: Set[str]
    loaded_crates: Dict[str, lang.LinkedExternCrate]

    @staticmethod
    def initial_crate(crate: lang.LinkedExternCrate) -> CollectCrateContext:
        return CollectCrateContext(crate.file, Path(()) / crate.name, set([crate.name]), {})

    def crate(self, crate: lang.LinkedExternCrate | hlir.LinkedExternCrate) -> CollectCrateContext:
        return CollectCrateContext(crate.file, Path(()) / crate.name, self.blacklist_crates | set([crate.name]), self.loaded_crates)

    def mod(self, mod: lang.LinkedMod) -> CollectCrateContext:
        return CollectCrateContext(mod.file, self.path / mod.name, set(self.blacklist_crates), self.loaded_crates)

    def load_crate(self, crate: str, crate_path: List[str], allow_hlir: bool, allow_lang: bool) -> lang.LinkedExternCrate:
        if crate in self.blacklist_crates:
            raise CollectCrateError(f"cyclical dependency on crate '{crate}'")

        if crate not in self.loaded_crates:
            self.loaded_crates[crate] = load_crate(crate, crate_path, self.blacklist_crates, allow_hlir, allow_lang)

        return self.loaded_crates[crate]

    def load_hlir_crate(self, crate: str, crate_path: List[str]) -> hlir.LinkedExternCrate:
        loaded_crate = self.load_crate(crate, crate_path, allow_hlir=True, allow_lang=False)
        assert isinstance(loaded_crate.file, hlir.SourceFile)
        return hlir.LinkedExternCrate(loaded_crate.name, loaded_crate.file)

def collect_crate(file_path: str, crate_path: List[str], allow_hlir: bool) -> lang.LinkedExternCrate:
    def visit_source_file(file: lang.SourceFile | hlir.SourceFile, ctx: CollectCrateContext, allow_hlir: bool):
        match file:
            case lang.SourceFile():
                visit_lang_source_file(file, ctx)
            case hlir.SourceFile() if allow_hlir:
                visit_hlir_source_file(file, ctx)
            case _:
                raise CollectCrateError(f"unexpected HLIR source file: {file.name} at {file.src}")

    def visit_lang_source_file(file: lang.SourceFile, ctx: CollectCrateContext):
        file.prog = visit_lang_program(file.prog, ctx)

    def visit_hlir_source_file(file: hlir.SourceFile, ctx: CollectCrateContext):
        file.prog = visit_hlir_program(file.prog, ctx)

    def visit_lang_program(prog: List[lang.Statement], ctx: CollectCrateContext) -> List[lang.Statement]:
        return [visit_lang_statement(stmt, ctx) for stmt in prog]

    def visit_lang_statement(stmt: lang.Statement, ctx: CollectCrateContext) -> lang.Statement:
        match stmt:
            case lang.ExternCrate(name):
                crate = ctx.load_crate(name, crate_path, allow_hlir=allow_hlir, allow_lang=True)
                visit_source_file(crate.file, ctx.crate(crate), allow_hlir=allow_hlir)
                return crate
            case lang.Mod(name, is_public):
                assert isinstance(ctx.cur, lang.SourceFile)
                mod = load_mod(ctx.path, ctx.cur, name, is_public)
                visit_lang_source_file(mod.file, ctx.mod(mod))
                return mod
            case _:
                return stmt

    def visit_hlir_program(prog: List[hlir.Statement], ctx: CollectCrateContext) -> List[hlir.Statement]:
        return [visit_hlir_statement(stmt, ctx) for stmt in prog]

    def visit_hlir_statement(stmt: hlir.Statement, ctx: CollectCrateContext) -> hlir.Statement:
        match stmt:
            case hlir.ExternCrate(name):
                crate = ctx.load_hlir_crate(name, crate_path)
                visit_hlir_source_file(crate.file, ctx.crate(crate))
                return crate
            case _:
                return stmt

    crate = load_initial_crate(file_path)
    visit_source_file(crate.file, CollectCrateContext.initial_crate(crate), allow_hlir=False)
    return crate
