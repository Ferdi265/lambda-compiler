from .collect import *
import os.path
import sys

def pretty_make_deps(crate_order: List[ModuleNamespace], outfile: str, output_dir: str, file: TextIO = sys.stdout):
    def get_name(mod: ModuleNamespace) -> str:
        return mod.get_name()

    def get_lambda(mod: ModuleNamespace) -> str:
        return mod.src

    def get_hlir(mod: ModuleNamespace) -> str:
        return os.path.join(output_dir, mod.get_name() + ".hlir")

    def get_hlis(mod: ModuleNamespace) -> str:
        return os.path.join(output_dir, mod.get_name() + ".hlis")

    def get_mlir(mod: ModuleNamespace) -> str:
        return os.path.join(output_dir, mod.get_name() + ".mlir")

    def get_llir(mod: ModuleNamespace, main: bool = False) -> str:
        return os.path.join(output_dir, mod.get_name() + (".main" if main else "") + ".ll")

    all_mod_deps = []
    for mod in crate_order:
        mod_crate_deps = mod.root.crate_order()[1:]
        mod_submod_deps = mod.mod_order()
        mod_name = mod.get_name()

        lambda_src = get_lambda(mod_submod_deps[0])
        lambda_mods = list(map(get_lambda, mod_submod_deps[1:]))

        hlir_src = get_hlir(mod)
        hlir_crate_deps = list(map(get_hlis, mod_crate_deps))
        print(f"{hlir_src}: {lambda_src} {' '.join(hlir_crate_deps + lambda_mods)}", end="\n\n", file=file)

        hlis_src = get_hlis(mod)
        print(f"{hlis_src}: {hlir_src}", end="\n\n", file=file)

        mlir_src = get_mlir(mod)
        mlir_crate_deps = list(map(get_mlir, mod_crate_deps))
        print(f"{mlir_src}: {hlir_src} {' '.join(mlir_crate_deps)}", end="\n\n", file=file)

        llir_src = get_llir(mod)
        print(f"{llir_src}: {mlir_src}", end="\n\n", file=file)

        all_mod_deps += list(map(get_lambda, mod_submod_deps))

    crate = crate_order[0]
    llir_main_src = get_llir(crate, main=True)
    llir_crate_deps = list(map(get_mlir, crate_order))
    print(f"{llir_main_src}: {' '.join(llir_crate_deps)}", end="\n\n", file=file)

    print(f"{outfile}: {' '.join(all_mod_deps)}", end="\n\n", file=file)

    for dep in all_mod_deps:
        print(f"{dep}:", end="\n\n", file=file)
