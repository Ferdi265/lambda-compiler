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
    print(f"# TESTCASE: {code = !r}, {globals = }")
    try:
        cur = parsed = parse(code)
        cur = resolved = resolve(parsed, globals)
        cur = rechained = rechain(resolved)
        cur = continuations = compute_continuations(rechained)
        cur = flattened = flatten_implementations(continuations)
    finally:
        pretty(cur)

for testcase in testcases:
    test(*testcase)
