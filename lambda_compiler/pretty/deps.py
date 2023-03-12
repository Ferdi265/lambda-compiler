from typing import *
from ..ast import lang_linked as lang
from ..ast import hlir_linked as hlir
from ..passes.lang.dep_order import SourceFile, crate_order, mod_order
import os.path
import sys

def pretty_make_deps(main_crate: SourceFile, outfile: str, output_dir: str, file: TextIO = sys.stdout):
    def get_name(mod: SourceFile) -> str:
        return mod.name

    def get_lambda(mod: SourceFile) -> str:
        return mod.src

    def get_hlir(mod: SourceFile) -> str:
        return os.path.join(output_dir, mod.name + ".hlir")

    def get_hlis(mod: SourceFile) -> str:
        return os.path.join(output_dir, mod.name + ".hlis")

    def get_mlir(mod: SourceFile, opt: bool = False) -> str:
        return os.path.join(output_dir, mod.name + (".opt" if opt else "") + ".mlir")

    def get_opt_mlir(mod: SourceFile, opt: bool = False) -> str:
        return get_mlir(mod, opt=True)

    def get_llir(mod: SourceFile, main: bool = False) -> str:
        return os.path.join(output_dir, mod.name + (".main" if main else "") + ".ll")

    all_mod_deps = []
    all_crate_order = crate_order(main_crate)
    for mod in all_crate_order:
        mod_crate_deps = crate_order(mod)[1:]
        mod_submod_deps = mod_order(mod)
        mod_name = mod.name

        lambda_src = get_lambda(mod_submod_deps[0])
        lambda_mods = list(map(get_lambda, mod_submod_deps[1:]))

        hlir_src = get_hlir(mod)
        hlir_crate_deps = list(map(get_hlis, mod_crate_deps))
        print(f"{hlir_src}: {lambda_src} {' '.join(hlir_crate_deps + lambda_mods)}", end="\n\n", file=file)

        hlis_src = get_hlis(mod)
        print(f"{hlis_src}: {hlir_src}", end="\n\n", file=file)

        mlir_src = get_mlir(mod)
        print(f"{mlir_src}: {hlir_src}", end="\n\n", file=file)

        mlir_opt_src = get_opt_mlir(mod)
        mlir_opt_crate_deps = list(map(get_opt_mlir, mod_crate_deps))
        print(f"{mlir_opt_src}: {mlir_src} {' '.join(mlir_opt_crate_deps)}", end="\n\n", file=file)

        llir_src = get_llir(mod)
        print(f"{llir_src}: {mlir_opt_src}", end="\n\n", file=file)

        all_mod_deps += list(map(get_lambda, mod_submod_deps))

    llir_main_src = get_llir(main_crate, main=True)
    llir_crate_deps = list(map(get_opt_mlir, all_crate_order))
    print(f"{llir_main_src}: {' '.join(llir_crate_deps)}", end="\n\n", file=file)

    print(f"{outfile}: {' '.join(all_mod_deps)}", end="\n\n", file=file)

    for dep in all_mod_deps:
        print(f"{dep}:", end="\n\n", file=file)
