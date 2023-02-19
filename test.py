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
    ("""
    ident = a -> a;
    y = g -> (f -> f f) f -> g x -> f f x;
    while = y while -> cond -> f -> initial -> (
        cond initial
            (x -> while cond f (f initial))
            (x -> initial)
        ident
    );
     """, set()),

    ("""
    y = g -> (f -> f f) f -> g x -> f f x;
    count = y count -> f -> initial -> nat ->
        nat
            (pred -> _ -> count f (f initial) pred)
            initial;
     """, set()),

    ("""
    y = g -> (f -> f f) f -> g x -> f f x;
    map = y map -> f -> list ->
        empty list
            (x -> nil)
            (x -> prepend (f (first list)) (map f (rest list)))
        ident;
    """, {"empty", "prepend", "first", "rest", "nil", "ident"}),

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
    );""", {"do", "ident", "puts", "list_n", "dec2", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}),

    ("""
    true = a -> b -> a;
    false = a -> b -> b;
    not = a -> a false true;
    and = a -> b -> a b false;
    or = a -> b -> a true b;
    never = a -> false;
    never2 = a -> a -> false;
    pair = a -> b -> sel -> sel a b;
    1st = p -> p true;
    2nd = p -> p false;
    ident = a -> a;
    y = g -> (f -> f f) f -> g x -> f f x;
    error = y (error -> _ -> error);
    do = y do -> arg -> f -> do (f arg);
    while = y while -> cond -> f -> initial ->
        cond initial
            (x -> while cond f (f initial))
            (x -> initial)
        ident;
    zero = false;
    succ = n -> s -> s n;
    pred = n -> n true zero;
    iszero = n -> n never2 true;
    count = y count -> f -> initial -> nat ->
        nat
            (pred -> _ -> count f (f initial) pred)
            initial;
    equal = y equal -> nat1 -> nat2 ->
        nat1
            (pred1 -> _ ->
                nat2
                    (pred2 -> _ -> equal pred1 pred2)
                    false
            )
            (iszero nat2);
    add = nat1 -> nat2 -> count succ nat1 nat2;
    sub = nat1 -> nat2 -> count pred nat1 nat2;
    mul = nat1 -> nat2 -> count (add nat1) zero nat2;
    0 = zero;
    1 = succ 0;
    2 = succ 1;
    3 = succ 2;
    4 = succ 3;
    5 = succ 4;
    6 = succ 5;
    7 = succ 6;
    8 = succ 7;
    9 = succ 8;
    10 = succ 9;
    dec2 = a -> b -> add (mul a 10) b;
    dec3 = a -> b -> c -> dec2 (dec2 a b) c;
    prepend = pair;
    first = 1st;
    rest = 2nd;
    nil = false;
    empty = list -> list (head -> tail -> _ -> false) true;
    map = y map -> f -> list ->
        empty list
            (x -> nil)
            (x -> prepend (f (first list)) (map f (rest list)))
        ident;
    zip = y zip -> f -> list1 -> list2 ->
        or (empty list1) (empty list2)
            (x -> nil)
            (x -> prepend (f (first list1) (first list2)) (zip f (rest list1) (rest list2)))
        ident;
    foldl = y foldl -> f -> initial -> list ->
        empty list
            (x -> initial)
            (x -> foldl f (f initial (first list)) (rest list))
        ident;
    prepend_all = y prepend_all -> list1 -> list2 ->
        empty list1
            (x -> list2)
            (x -> prepend_all (rest list1) (prepend (first list1) list2))
        ident;
    reverse = list -> prepend_all list nil;
    append = list -> el -> prepend_all (reverse list) (prepend el nil);
    append_n = y append_n -> nat -> list ->
        iszero nat
            (x -> list)
            (x -> el -> append_n (pred nat) (append list el))
        ident;
    list_n = nat -> append_n nat nil;
    """, set())
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
        cur = instantiated = instantiate_implementations(renumbered)
        cur = dedup = dedup_implementations(instantiated)
        pretty_mlir(cur)
    except Exception:
        pretty(cur)
        raise

for testcase in testcases:
    test(*testcase)
