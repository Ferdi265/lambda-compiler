filename = "src/io.lambda"
source = r"""
extern crate std;
use std::*;

extern impure lambda_io_zero;
extern impure lambda_io_succ;
extern impure lambda_io_pred;
extern impure lambda_io_iszero;
extern impure lambda_io_putc;
extern impure lambda_io_getc;
extern impure lambda_io_debug;

impure nat2c = n -> count lambda_io_succ lambda_io_zero n;

impure c2nat = n -> 2nd (while
    (p -> not (lambda_io_iszero (1st p)))
    (p -> pair
        (lambda_io_pred (1st p))
        (succ (2nd p))
    )
    (pair n zero)
);

pub eof = dec3 2 5 6;

pop_eof = list ->
    equal (first list) eof
        (x -> rest list)
        (x -> list)
    ident;

pub impure putc = n -> lambda_io_putc (nat2c n);

pub impure puts = s -> map putc s;

pub impure getc = x -> c2nat (lambda_io_getc x);

pub impure gets = x -> reverse (pop_eof (while
    (l -> not (or (equal (first l) eof) (equal (first l) 10)))
    (l -> prepend (getc ident) l)
    (prepend (getc ident) nil)
));

pub impure trap = lambda_io_debug;
""".strip()
