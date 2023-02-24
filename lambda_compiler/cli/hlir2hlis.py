from lambda_compiler import *
import lambda_compiler
import argparse
import os.path
import sys

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "strip lambda HLIR to HLIS"
    )

    ap.add_argument("input", help = "the input HLIR file", nargs = "?")
    ap.add_argument("-o", "--output", help = "the output HLIS file")
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

    outfile = args.output
    if outfile is None:
        outfile = os.path.join(infile_dir, infile_name + ".hlis")

    with open(infile, "r") as f:
        code = f.read()

    ast = parse_hlir(code, stub=True)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        pretty_hlir(ast, file=f, stub=True)

if __name__ == "__main__":
    main()
