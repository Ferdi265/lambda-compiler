from .collect import *
import os.path
import sys

def pretty_make_deps(crate_order: List[ModuleNamespace], output_dir: str, file: TextIO = sys.stdout):
    def get_lambda(mod: ModuleNamespace) -> str:
        return mod.src

    def get_hlir(mod: ModuleNamespace) -> str:
        return os.path.join(output_dir, mod.get_name() + ".hlir")

    def get_mlir(mod: ModuleNamespace) -> str:
        return os.path.join(output_dir, mod.get_name() + ".mlir")

    for mod in crate_order:
        mod_crate_deps = mod.root.crate_order()[1:]
        mod_submod_deps = mod.mod_order()
        mod_name = mod.get_name()

        hlir_src = os.path.join(output_dir, mod_name + ".hlir")
        hlir_crate_deps = list(map(get_hlir, mod_crate_deps))
        lambda_mod_deps = list(map(get_lambda, mod_submod_deps))
        hlir_deps = " ".join(hlir_crate_deps + lambda_mod_deps)
        print(f"{hlir_src}: {hlir_deps}", end="\n\n", file=file)

        mlir_src = os.path.join(output_dir, mod_name + ".mlir")
        mlir_crate_deps = list(map(get_mlir, mod_crate_deps))
        mlir_deps = " ".join(mlir_crate_deps + [hlir_src])
        print(f"{mlir_src}: {mlir_deps}", end="\n\n", file=file)
