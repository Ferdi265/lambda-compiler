from __future__ import annotations
from typing import *
from dataclasses import dataclass, field
from .collect import *
import os.path

class LoaderError(Exception):
    pass

@dataclass
class NopLoader(Loader):
    def load_crate(self, crate: str) -> ModuleNamespace:
        raise LoaderError("not implemented")
    def load_mod(self, mod: ModuleNamespace, name: str) -> ModuleNamespace:
        raise LoaderError("not implemented")

@dataclass
class FileListLoader(Loader):
    files: List[str]

    def load_crate(self, crate: str) -> ModuleNamespace:
        for file in self.files:
            file_name = os.path.basename(file).split(".", 1)[0]
            if file_name == crate:
                break
        else:
            raise LoaderError(f"did not find crate '{crate}'")

        if not os.path.isfile(file):
            raise LoaderError(f"did not find crate '{crate}' at {file}")

        root = RootNamespace()
        collect_crate(file, crate, self, root)

        mod = root.crates[crate]
        mod.strip_private()
        return mod

    def load_mod(self, mod: ModuleNamespace, name: str) -> ModuleNamespace:
        dir = mod.dir
        src = os.path.join(dir, name + ".lambda")
        if not os.path.isfile(src):
            raise LoaderError(f"did not find module '{mod.path / name}' at {src}")

        submod = ModuleNamespace(mod.root, mod, mod.path / name, src, dir)
        return submod
