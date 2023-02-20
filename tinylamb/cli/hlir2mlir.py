from tinylamb import *
import sys

def main():
    args = sys.argv[1:]

    if len(args) == 1:
        file, crate = args[0], parse_path("main")
    elif len(args) == 2:
        file, crate = args[0], parse_path(args[1])
    else:
        print("usage: hlir2mlir <file> [crate]", file = sys.stderr)
        sys.exit(1)

    with open(file, "r") as f:
        code = f.read()

    ast = parse(code)
    ast = resolve(ast, crate, OrderedSet())
    ast = rechain(ast)
    ast = compute_continuations(ast)
    ast = flatten_implementations(ast)
    ast = renumber_captures(ast)
    ast = instantiate_implementations(ast)
    ast = dedup_implementations(ast)
    pretty_mlir(ast)

if __name__ == "__main__":
    main()
