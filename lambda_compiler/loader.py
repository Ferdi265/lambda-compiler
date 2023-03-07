from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from .collect import *
from .parse_mlir import *
import os.path

class LoaderError(Exception):
    pass

@dataclass
class NopLoader(Loader):
    def load_crate(self, parent: RootNamespace, crate: str) -> ModuleNamespace:
        raise LoaderError("not implemented")
    def load_mod(self, mod: ModuleNamespace, name: str) -> ModuleNamespace:
        raise LoaderError("not implemented")

@dataclass
class CratePathLoader(Loader):
    crate_path: List[str]
    allow_hlir: bool = True

    def initial_crate_name_and_dir(self, file_path: str) -> CrateInfo:
        file_name = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        dir_name = os.path.basename(dir_path)

        crate_name = dir_name
        crate_dir = dir_path
        crate_src = file_path
        if os.path.isfile(crate_src) and file_name == "mod.lambda":
            return CrateInfo(crate_name, file_path, dir_path, True)

        crate_name = file_name
        crate_dir = file_path
        crate_src = os.path.join(crate_dir, "mod.lambda")
        if os.path.isfile(crate_src):
            return CrateInfo(crate_name, file_path, dir_path, True)

        crate_name = file_name.split(".", 1)[0]
        crate_dir = dir_path
        crate_src = file_path
        if os.path.isfile(crate_src) and crate_name != "mod":
            return CrateInfo(crate_name, file_path, dir_path, False)

        raise LoaderError(f"could not determine crate name and dir from path {file_path}")

    def load_crate(self, parent: RootNamespace, crate: str) -> ModuleNamespace:
        if crate in parent.blacklist_crates:
            raise LoaderError(f"cyclical dependency on crate '{crate}'")

        for dir in self.crate_path:
            crate_src = os.path.join(dir, f"{crate}.hlis")
            is_hlis = True
            if self.allow_hlir and os.path.isfile(crate_src):
                break

            crate_src = os.path.join(dir, f"{crate}.hlir")
            is_hlis = True
            if self.allow_hlir and os.path.isfile(crate_src):
                break

            crate_src = os.path.join(dir, f"{crate}.lambda")
            is_hlis = False
            if os.path.isfile(crate_src):
                break

            crate_src = os.path.join(dir, f"{crate}/mod.lambda")
            is_hlis = False
            if os.path.isfile(crate_src):
                break
        else:
            raise LoaderError(f"did not find crate '{crate}'")

        root = RootNamespace(crate)
        root.blacklist_crates |= parent.blacklist_crates
        collect_crate(crate_src, self, root, stub = is_hlis)

        mod = root.crates[crate]
        mod.strip_private()
        return mod

    def load_crate_mlir(self, crate: str) -> List[Statement]:
        for dir in self.crate_path:
            crate_src = os.path.join(dir, f"{crate}.mlir")
            if os.path.isfile(crate_src):
                break
        else:
            raise LoaderError(f"did not find crate '{crate}'")

        with open(crate_src) as f:
            code = f.read()
            return parse_mlir(code, crate_src)

    def load_mod(self, mod: ModuleNamespace, name: str) -> ModuleNamespace:
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
            mod_dir = os.path.join(mod.dir, mod.get_name())
            mod_src = os.path.join(mod_dir, f"{name}.lambda")
            owns_dir = False
            if os.path.isfile(mod_src):
                found = True

        if not found and not mod.owns_dir:
            mod_dir = os.path.join(mod.dir, mod.get_name(), name)
            mod_src = os.path.join(mod_dir, "mod.lambda")
            owns_dir = True
            if os.path.isfile(mod_src):
                found = True

        if not found:
            raise LoaderError(f"did not find module '{mod.path / name}'")

        submod = ModuleNamespace(mod.root, mod, mod.path / name, mod_src, mod_dir, owns_dir)
        return submod
