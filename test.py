from typing import *
from tinylamb import *

testcases: List[Tuple[str, Set[str]]] = [
    ("ident = a -> a;", set()),
    ("true = a -> b -> a;", set()),
    ("false = a -> b -> b;", set()),

    ("not = a -> a false true;", {"true", "false"}),
    ("and = a -> b -> a b false;", {"true", "false"}),
    ("or = a -> b -> a true b;", {"true", "false"}),
    ("xor = a -> b -> a (not b) b;", {"true", "false", "not"}),

    ("pair = a -> b -> sel -> sel a b;", set()),
    ("y = g -> (f -> f f) f -> g x -> f f x;", set()),
    ("""while = y while -> cond -> f -> initial -> (
        cond initial
            (x -> while cond f (f initial))
            (x -> initial)
        ident
    );""", {"y", "ident"}),

    ("""main = _ -> (do ident
        (_ -> puts (list_n 6
            (dec2 7 2)
            (dec2 1 0 1)
            (dec2 1 0 8)
            (dec2 1 0 8)
            (dec2 1 1 1)
            (dec2 1 0)
        ))
        (_ -> puts (list_n 6
            (dec2 8 7)
            (dec2 1 1 1)
            (dec2 1 1 4)
            (dec2 1 0 8)
            (dec2 1 0 0)
            (dec2 1 0)
        ))
    );""", {"do", "ident", "puts", "list_n", "dec2", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"})
]

def test(code: str, globals: Set[str]):
    name = code.split("=", 1)[0].strip()
    print(f"# TESTCASE {name}: {globals = }")
    try:
        cur = parsed = parse(code)
        cur = resolved = resolve(parsed, globals)
        cur = rechained = rechain(resolved)
        cur = continuations = compute_continuations(rechained)
        cur = flattened = flatten_implementations(continuations)
        cur = renumbered = renumber_captures(flattened)
        pretty_mlir(cur)
    except Exception:
        pretty(cur)
        raise

for testcase in testcases:
    test(*testcase)
