from ...ast.mlir import *
from ...parse.mlir import parse_mlir
from ...ordered_set import OrderedSet
import os.path

class CollectDepsError(Exception):
    pass

def load_crate(crate: str, crate_path: List[str]) -> List[Statement]:
    for dir in crate_path:
        crate_src = os.path.join(dir, f"{crate}.opt.mlir")
        if os.path.isfile(crate_src):
            break

        crate_src = os.path.join(dir, f"{crate}.mlir")
        if os.path.isfile(crate_src):
            break
    else:
        raise CollectDepsError(f"did not find crate '{crate}'")

    with open(crate_src) as f:
        code = f.read()
        return parse_mlir(code, crate_src)

def collect_deps(crate: str, prog: List[Statement], crate_path: List[str]) -> Tuple[List[Statement], List[str]]:
    found_crates: OrderedSet[str] = OrderedSet()
    crate_order: List[str] = []
    collected: List[Statement] = []

    def collect_crate(crate: str, prog: List[Statement], collect: bool):
        nonlocal collected

        for other in referenced_crates(prog):
            if other not in found_crates:
                found_crates.add(other)
                collect_crate(other, load_crate(other, crate_path), collect=True)

        crate_order.append(crate)

        if collect:
            collected += prog

    def referenced_crates(prog: List[Statement]) -> OrderedSet[str]:
        ref_crates: OrderedSet[str] = OrderedSet()

        for stmt in prog:
            match stmt:
                case ExternCrate(crate):
                    ref_crates.add(crate)

        return ref_crates

    collect_crate(crate, prog, collect=False)
    return collected, crate_order
