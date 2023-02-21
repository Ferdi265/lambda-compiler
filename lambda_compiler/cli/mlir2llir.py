from lambda_compiler import *
import lambda_compiler
import argparse
import os.path
import sys

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "compile lambda MLIR to LLVM IR"
    )

    ap.add_argument("input", help = "the input MLIR file", nargs = "?")
    ap.add_argument("-o", "--output", help = "the output LLIR file")
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

    arch = Architecture(
        triple = "x86_64-pc-linux-gnu",
        data_layout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128",
        ptr_size = 8,
        ptr_align = 8
    )

    ast = parse_mlir(code)
    llir = generate_llir(ast, crate, arch)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        f.write(llir)

if __name__ == "__main__":
    main()
