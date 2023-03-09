from lambda_compiler.legacy import *
import lambda_compiler
import argparse
import platform
import os.path
import sys

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "compile lambda MLIR to LLVM IR"
    )

    ap.add_argument("input", help = "the input MLIR file", nargs = "?")
    ap.add_argument("-o", "--output", help = "the output LLIR file")
    ap.add_argument("-c", "--crate-name", help = "set the name of the compiled crate")
    ap.add_argument("-t", "--target", help = "set the architecture to compile for")
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
        outfile = os.path.join(infile_dir, infile_name + ".ll")

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
    llir = generate_llir(ast, crate, arch)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        f.write(llir)

if __name__ == "__main__":
    main()
