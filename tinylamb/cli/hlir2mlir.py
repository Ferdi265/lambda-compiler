from tinylamb import *
import argparse
import os.path
import sys

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description = "compile lambda HLIR to MLIR"
    )

    ap.add_argument("input", help = "the input HLIR file")
    ap.add_argument("-o", "--output", help = "the output MLIR file")
    ap.add_argument("-c", "--crate-name", help = "the name of the compiled crate")

    return ap.parse_args()

def main():
    args = parse_args()

    infile = args.input
    infile_dir = os.path.dirname(infile)
    infile_name = os.path.basename(infile).split(".", 1)[0]

    crate = args.crate_name
    if crate is None:
        crate = infile_name

    outfile = args.output
    if outfile is None:
        outfile = os.path.join(infile_dir, infile_name + ".mlir")

    with open(infile, "r") as f:
        code = f.read()

    ast = parse(code)
    ast = demacro(ast)
    ast = resolve(ast, parse_path(crate))
    ast = rechain(ast)
    ast = compute_continuations(ast)
    ast = flatten_implementations(ast)
    ast = renumber_captures(ast)
    ast = instantiate_implementations(ast)
    ast = dedup_implementations(ast)

    if outfile == "-":
        pretty_mlir(ast, file=sys.stdout)
    else:
        with open(outfile, "w") as f:
            pretty_mlir(ast, file=f)

if __name__ == "__main__":
    main()
