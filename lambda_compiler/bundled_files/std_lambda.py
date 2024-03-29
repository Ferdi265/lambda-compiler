filename = "src/std.lambda"
source = r"""
pub true = a -> b -> a;
pub false = a -> b -> b;

pub not = a -> a false true;
pub and = a -> b -> a b false;
pub or = a -> b -> a true b;

pub never = a -> false;
pub never2 = a -> a -> false;

pub pair = a -> b -> sel -> sel a b;
pub 1st = p -> p true;
pub 2nd = p -> p false;

pub ident = a -> a;
pub y = g -> (f -> f f) f -> g x -> f f x;
pub error = y (error -> _ -> error);
pub do = y do -> arg -> f -> do (f arg);

pub while = y while -> cond -> f -> initial ->
    cond initial
        (x -> while cond f (f initial))
        (x -> initial)
    ident;

pub zero = false;
pub succ = n -> s -> s n;
pub pred = n -> n true zero;
pub iszero = n -> n never2 true;

pub count = y count -> f -> initial -> nat ->
    nat
        (pred -> _ -> count f (f initial) pred)
        initial;

pub equal = y equal -> nat1 -> nat2 ->
    nat1
        (pred1 -> _ ->
            nat2
                (pred2 -> _ -> equal pred1 pred2)
                false
        )
        (iszero nat2);

pub less = y less -> a -> b ->
    iszero a
        (x -> not (iszero b))
        (x -> less (pred a) (pred b))
    ident;

pub greater = a -> b -> less b a;

pub add = nat1 -> nat2 -> count succ nat1 nat2;
pub sub = nat1 -> nat2 -> count pred nat1 nat2;
pub mul = nat1 -> nat2 -> count (add nat1) zero nat2;

pub divmod = a -> b -> y (div -> acc -> r ->
        less acc b
            (x -> pair r acc)
            (x -> div (sub acc b) (succ r))
        ident
    ) a zero;

pub div = a -> b -> 1st (divmod a b);
pub rem = a -> b -> 2nd (divmod a b);

pub 0 = zero;
pub 1 = succ 0;
pub 2 = succ 1;
pub 3 = succ 2;
pub 4 = succ 3;
pub 5 = succ 4;
pub 6 = succ 5;
pub 7 = succ 6;
pub 8 = succ 7;
pub 9 = succ 8;
pub 10 = succ 9;

pub dec2 = a -> b -> add (mul a 10) b;
pub dec3 = a -> b -> c -> dec2 (dec2 a b) c;

pub prepend = pair;
pub first = 1st;
pub rest = 2nd;
pub nil = false;

pub empty = list -> list (head -> tail -> _ -> false) true;

pub map = y map -> f -> list ->
    empty list
        (x -> nil)
        (x -> prepend (f (first list)) (map f (rest list)))
    ident;

pub zip = y zip -> f -> list1 -> list2 ->
    or (empty list1) (empty list2)
        (x -> nil)
        (x -> prepend (f (first list1) (first list2)) (zip f (rest list1) (rest list2)))
    ident;

pub foldl = y foldl -> f -> initial -> list ->
    empty list
        (x -> initial)
        (x -> foldl f (f initial (first list)) (rest list))
    ident;

pub prepend_all = y prepend_all -> list1 -> list2 ->
    empty list1
        (x -> list2)
        (x -> prepend_all (rest list1) (prepend (first list1) list2))
    ident;

pub reverse = list -> prepend_all list nil;

pub append = list -> el -> prepend_all (reverse list) (prepend el nil);

pub append_n = y append_n -> nat -> list ->
    iszero nat
        (x -> list)
        (x -> el -> append_n (pred nat) (append list el))
    ident;

pub list_n = nat -> append_n nat nil;
""".strip()
