from tinylamb import *
import sys

def main():
    args = sys.argv[1:]

    crate: Optional[str] = None
    if len(args) == 1:
        file = args[0]
    elif len(args) == 2:
        file, crate = args[0], args[1]
    else:
        print("usage: hlir2mlir <file> [crate]", file = sys.stderr)
        sys.exit(1)

    with open(file, "r") as f:
        code = f.read()

    ast = parse(code)
    ast = resolve(ast, OrderedSet())
    ast = rechain(ast)
    ast = compute_continuations(ast)
    ast = flatten_implementations(ast)
    ast = renumber_captures(ast)
    ast = instantiate_implementations(ast)
    ast = dedup_implementations(ast)
    pretty_mlir(ast, crate)

if __name__ == "__main__":
    main()
