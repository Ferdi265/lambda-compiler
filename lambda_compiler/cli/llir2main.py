from lambda_compiler import *
import lambda_compiler
import argparse
import platform
import os.path
import sys

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "generate main and initializer functions for lambda LLVM IR"
    )

    ap.add_argument("crates", help = "the program crates, in initialization order, main crate last", nargs = "+")
    ap.add_argument("-o", "--output", help = "the output LLIR file")
    ap.add_argument("-t", "--target", help = "set the architecture to compile for")
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

    target = args.target
    if target is None:
        target = platform.machine()

    if target not in TARGETS:
        print(f"error: unsupported target '{target}'", file = sys.stderr)
        print("info: supported targets: " + ", ".join(TARGETS), file = sys.stderr)
        sys.exit(1)

    arch = TARGETS[target]

    llir = generate_main_llir(crates, arch)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        f.write(llir)

if __name__ == "__main__":
    main()
