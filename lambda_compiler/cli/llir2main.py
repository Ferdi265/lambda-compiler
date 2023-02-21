from lambda_compiler import *
import lambda_compiler
import argparse
import os.path
import sys

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "generate main and initializer functions for lambda LLVM IR"
    )

    ap.add_argument("crates", help = "the program crates, in initialization order, main crate last", nargs = "+")
    ap.add_argument("-o", "--output", help = "the output LLIR file")
    ap.add_argument("-v", "--version", action = "store_true", help = "print current version and exit")

    return ap, ap.parse_args()

def main():
    ap, args = parse_args()

    if args.version:
        print(f"{ap.prog} {lambda_compiler.__version__}")
        return

    crates = args.crates

    outfile = args.output
    if outfile is None:
        outfile = crates[-1] + ".main.ll"

    arch = Architecture(
        triple = "x86_64-pc-linux-gnu",
        data_layout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128",
        ptr_size = 8,
        ptr_align = 8
    )

    llir = generate_main_llir(crates, arch)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        f.write(llir)

if __name__ == "__main__":
    main()
