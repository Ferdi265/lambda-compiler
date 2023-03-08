from .parse_mlir import *
from .loader import *
from .orderedset import *

def collect_mlir(crate: str, infile: str, loader: Loader) -> Tuple[List[Statement], List[str]]:
    found_crates: OrderedSet[str] = OrderedSet()
    crate_order: List[str] = []
    collected: List[Statement] = []

    def collect_file(crate: str, infile: str):
        with open(infile) as f:
            code = f.read()
            prog = parse_mlir(code, infile)
            collect_crate(crate, prog)

    def collect_crate(crate: str, prog: List[Statement]):
        for other in referenced_crates(prog):
            if other not in found_crates:
                found_crates.add(other)
                collect_crate(other, loader.load_crate_mlir(other))

        crate_order.append(crate)

    def referenced_crates(prog: List[Statement]) -> OrderedSet[str]:
        ref_crates: OrderedSet[str] = OrderedSet()

        for stmt in prog:
            match stmt:
                case ExternCrate(crate):
                    ref_crates.add(crate)

        return ref_crates

    collect_file(crate, infile)
    return collected, crate_order
