from lambda_compiler import *
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
    ap.add_argument("-P", "--crate-path", action = "append", help = "add a directory to the crate search path")
    ap.add_argument("--no-default-crate-path", action = "store_true", default=False, help = "do not use default crate search paths")
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

    crate_path = get_crate_search_path(args.crate_path or [], not args.no_default_crate_path)

    crate = args.crate_name
    if crate is None:
        crate = infile_name

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
    loader = CratePathLoader(crate_path)
    deps_ast, crates = collect_mlir_deps(crate, ast, loader)
    deps_ast = resolve_mlir(deps_ast)
    ast = instantiate_implementations(ast, deps_ast)

    with sys.stdout if outfile == "-" else open(outfile, "w") as f:
        pretty_mlir(ast, file=f)

if __name__ == "__main__":
    main()
