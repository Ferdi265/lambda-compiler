from lambda_compiler import *
import lambda_compiler
import argparse
import os.path
import sys

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "compile Lambda to HLIR"
    )

    ap.add_argument("input", help = "the input Lambda file", nargs = "?")
    ap.add_argument("-o", "--output", help = "the output HLIR file")
    ap.add_argument("-c", "--crate-name", help = "set the name of the compiled crate")
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

    crate = args.crate_name
    if crate is None:
        crate = infile_name

    outfile = args.output
    if outfile is None:
        outfile = os.path.join(infile_dir, infile_name + ".mlir")

    with open(infile, "r") as f:
        code = f.read()

    ast = parse_lang(code)
    ast = demacro(ast)
    ast = resolve(ast, crate, keep_extern=True)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        pretty_hlir(ast, file=f)

if __name__ == "__main__":
    main()
