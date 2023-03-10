from lambda_compiler.legacy import *
import lambda_compiler
import argparse
import os.path
import sys

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "compile lambda HLIR to MLIR"
    )

    ap.add_argument("input", help = "the input HLIR file", nargs = "?")
    ap.add_argument("-o", "--output", help = "the output MLIR file")
    ap.add_argument("-v", "--version", action = "store_true", help = "print current version and exit")

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

    outfile = args.output
    if outfile is None:
        outfile = os.path.join(infile_dir, infile_name + ".mlir")

    with open(infile, "r") as f:
        code = f.read()

    ast = parse_hlir(code, infile)
    ast = resolve(ast)
    ast = rechain(ast)
    ast = compute_continuations(ast)
    ast = flatten_implementations(ast)
    ast = renumber_captures(ast)
    ast = reorder_implementations(ast)
    ast = add_definitions(ast)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        pretty_mlir(ast, file=f)

if __name__ == "__main__":
    main()
