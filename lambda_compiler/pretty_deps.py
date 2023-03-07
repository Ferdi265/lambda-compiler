from .collect import *
import os.path
import sys

def pretty_make_deps(crate_order: List[ModuleNamespace], outfile: str, output_dir: str, file: TextIO = sys.stdout):
    def get_lambda(mod: ModuleNamespace) -> str:
        return mod.src

    def get_hlir(mod: ModuleNamespace) -> str:
        return os.path.join(output_dir, mod.get_name() + ".hlir")

    def get_mlir(mod: ModuleNamespace) -> str:
        return os.path.join(output_dir, mod.get_name() + ".mlir")

    all_mod_deps = []
    for mod in crate_order:
        mod_crate_deps = mod.root.crate_order()[1:]
        mod_submod_deps = mod.mod_order()
        mod_name = mod.get_name()

        lambda_src = get_lambda(mod_submod_deps[0])
        lambda_mods = list(map(get_lambda, mod_submod_deps[1:]))

        hlir_src = os.path.join(output_dir, mod_name + ".hlir")
        hlir_crate_deps = list(map(get_hlir, mod_crate_deps))
        print(f"{hlir_src}: {lambda_src} | {outfile} {' '.join(hlir_crate_deps + lambda_mods)}", end="\n\n", file=file)

        mlir_src = os.path.join(output_dir, mod_name + ".mlir")
        mlir_crate_deps = list(map(get_mlir, mod_crate_deps))
        print(f"{mlir_src}: {hlir_src} | {outfile} {' '.join(mlir_crate_deps)}", end="\n\n", file=file)

        all_mod_deps += list(map(get_lambda, mod_submod_deps))

    print(f"{outfile}: | {' '.join(all_mod_deps)}", end="\n\n", file=file)
