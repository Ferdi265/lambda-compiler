from __future__ import annotations
from ...ast.lang_linked import *
from ...ast.hlir_linked import LinkedExternCrate as HLIRLinkedExternCrate
from ...ast import hlir
from ...parse.lang import parse_lang
from ...parse.hlir import parse_hlir
import os.path

class CollectCrateError(Exception):
    pass

def load_initial_crate(file_path: str) -> LinkedExternCrate:
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

    return LinkedExternCrate(crate_name, crate_dir, crate_src, owns_dir, prog)

def load_crate(crate: str, crate_path: List[str], blacklist_crates: Set[str], allow_hlir: bool = True, allow_lang: bool = True) -> LinkedExternCrate:
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

    prog: List[Statement] | List[hlir.Statement]
    with open(crate_src, "r") as f:
        code = f.read()
        if is_hlir:
            prog = parse_hlir(code, crate_src, stub=True)
        else:
            prog = parse_lang(code, crate_src)

    return LinkedExternCrate(crate, crate_dir, crate_src, owns_dir, prog)

def load_hlir_crate(crate: str, crate_path: List[str], blacklist_crates: Set[str]) -> HLIRLinkedExternCrate:
    linked_crate = load_crate(crate, crate_path, blacklist_crates, allow_hlir=True, allow_lang=False)
    return HLIRLinkedExternCrate(
        linked_crate.name, linked_crate.dir, linked_crate.src, linked_crate.owns_dir,
        cast(List[hlir.Statement], linked_crate.prog)
    )

def load_mod(path: Path, mod: LinkedMod | LinkedExternCrate | HLIRLinkedExternCrate, name: str, is_public: bool) -> LinkedMod:
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

    return LinkedMod(name, is_public, mod_dir, mod_src, owns_dir, prog)

@dataclass
class CollectCrateContext:
    cur: LinkedMod | LinkedExternCrate | HLIRLinkedExternCrate
    path: Path

    blacklist_crates: Set[str]

    @staticmethod
    def initial_crate(crate: LinkedExternCrate) -> CollectCrateContext:
        return CollectCrateContext(crate, Path(()) / crate.name, set([crate.name]))

    def crate(self, crate: LinkedExternCrate | HLIRLinkedExternCrate) -> CollectCrateContext:
        return CollectCrateContext(crate, Path(()) / crate.name, self.blacklist_crates | set([crate.name]))

    def mod(self, mod: LinkedMod) -> CollectCrateContext:
        return CollectCrateContext(mod, self.path / mod.name, set(self.blacklist_crates))

def collect_crate(file_path: str, crate_path: List[str], allow_hlir: bool) -> LinkedExternCrate:
    def visit_lang_program(prog: List[Statement], ctx: CollectCrateContext) -> List[Statement]:
        return [visit_lang_statement(stmt, ctx) for stmt in prog]

    def visit_lang_statement(stmt: Statement, ctx: CollectCrateContext) -> Statement:
        match stmt:
            case ExternCrate(name):
                crate = load_crate(name, crate_path, ctx.blacklist_crates, allow_hlir=allow_hlir, allow_lang=True)
                return visit_lang_extern_crate(crate, ctx.crate(crate))
            case Mod(name, is_public):
                mod = load_mod(ctx.path, ctx.cur, name, is_public)
                return visit_lang_mod(mod, ctx.mod(mod))
            case _:
                return stmt

    def visit_lang_extern_crate(crate: LinkedExternCrate, ctx: CollectCrateContext) -> LinkedExternCrate:
        if len(crate.prog) == 0 or isinstance(crate.prog[0], Statement):
            crate.prog = visit_lang_program(cast(List[Statement], crate.prog), ctx)
        elif allow_hlir:
            crate.prog = visit_hlir_program(cast(List[hlir.Statement], crate.prog), ctx)
        else:
            raise CollectCrateError(f"unexpected HLIR crate: {crate.name} at {crate.src}")

        return crate

    def visit_lang_mod(mod: LinkedMod, ctx: CollectCrateContext) -> LinkedMod:
        mod.prog = visit_lang_program(mod.prog, ctx)
        return mod

    def visit_hlir_program(prog: List[hlir.Statement], ctx: CollectCrateContext) -> List[hlir.Statement]:
        return [visit_hlir_statement(stmt, ctx) for stmt in prog]

    def visit_hlir_statement(stmt: hlir.Statement, ctx: CollectCrateContext) -> hlir.Statement:
        match stmt:
            case hlir.ExternCrate(name):
                crate = load_hlir_crate(name, crate_path, ctx.blacklist_crates)
                return visit_hlir_extern_crate(crate, ctx.crate(crate))
            case _:
                return stmt

    def visit_hlir_extern_crate(crate: HLIRLinkedExternCrate, ctx: CollectCrateContext) -> HLIRLinkedExternCrate:
        crate.prog = visit_hlir_program(crate.prog, ctx)
        return crate

    crate = load_initial_crate(file_path)
    return visit_lang_extern_crate(crate, CollectCrateContext.initial_crate(crate))
