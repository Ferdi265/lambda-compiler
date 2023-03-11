from typing import *
from lambda_compiler.version import __version__
from lambda_compiler.search_path import get_crate_search_path
from lambda_compiler.passes.lang.collect_deps import collect_crate
from lambda_compiler.pretty.deps import pretty_make_deps
import argparse
import os.path
import sys

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "collect dependency information for compiling Lambda programs"
    )

    ap.add_argument("input", help = "the input Lambda file", nargs = "?")
    ap.add_argument("-o", "--output", help = "the output deps file")
    ap.add_argument("-O", "--output-dir", help = "the output directory where build artifacts are expected")
    ap.add_argument("-P", "--crate-path", action = "append", help = "add a directory to the crate search path")
    ap.add_argument("--no-default-crate-path", action = "store_true", default=False, help = "do not use default crate search paths")
    ap.add_argument("-v", "--version", action = "store_true", default=False, help = "print current version and exit")

    return ap, ap.parse_args()

def main():
    ap, args = parse_args()

    if args.version:
        print(f"{ap.prog} {lambda_compiler.__version__}")
        return

    infile = args.input
    if infile is None:
        ap.print_help()
        return

    infile_dir = os.path.dirname(infile)
    infile_name = os.path.basename(infile).split(".", 1)[0]

    crate_path = get_crate_search_path(args.crate_path or [], not args.no_default_crate_path)

    outfile = args.output
    if outfile is None:
        outfile = os.path.join(infile_dir, infile_name + ".d")

    output_dir = args.output_dir
    if output_dir is None:
        output_dir = "."

    crate = collect_crate(infile, crate_path, allow_hlir=False)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        pretty_make_deps(crate.file, outfile, output_dir, file=f)

if __name__ == "__main__":
    main()
