from typing import *
from lambda_compiler.version import __version__
from lambda_compiler.search_path import get_crate_search_path
from lambda_compiler.parse.mlir import parse_mlir
from lambda_compiler.passes.mlir.collect_deps import collect_deps
from lambda_compiler.passes.llir.generate import generate_main_llir
from lambda_compiler.passes.llir.target import TARGETS
import argparse
import platform
import os.path
import sys

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "compile lambda MLIR to main and initializer functions LLVM IR"
    )

    ap.add_argument("input", help = "the input MLIR file", nargs = "?")
    ap.add_argument("-o", "--output", help = "the output LLIR file")
    ap.add_argument("-P", "--crate-path", action = "append", help = "add a directory to the crate search path")
    ap.add_argument("--no-default-crate-path", action = "store_true", default=False, help = "do not use default crate search paths")
    ap.add_argument("-c", "--crate-name", help = "set the name of the compiled crate")
    ap.add_argument("-t", "--target", help = "set the architecture to compile for")
    ap.add_argument("-v", "--version", action = "store_true", help = "print current version and exit")

    return ap, ap.parse_args()

def main():
    ap, args = parse_args()

    if args.version:
        print(f"{ap.prog} {__version__}")
        return

    infile = args.input
    if infile is None:
        ap.print_help()
        return

    infile_dir = os.path.dirname(infile)
    infile_name = os.path.basename(infile).split(".", 1)[0]

    crate_path = get_crate_search_path(args.crate_path or [], not args.no_default_crate_path)

    crate = args.crate_name
    if crate is None:
        crate = infile_name

    outfile = args.output
    if outfile is None:
        outfile = os.path.join(infile_dir, infile_name + ".main.ll")

    target = args.target
    if target is None:
        target = platform.machine()

    if target not in TARGETS:
        print(f"error: unsupported target '{target}'", file = sys.stderr)
        print("info: supported targets: " + ", ".join(TARGETS), file = sys.stderr)
        sys.exit(1)

    arch = TARGETS[target]

    with open(infile, "r") as f:
        code = f.read()

    ast = parse_mlir(code, infile)
    deps_ast, crates = collect_deps(crate, ast, crate_path)
    llir = generate_main_llir(crates, arch)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        f.write(llir)

if __name__ == "__main__":
    main()
