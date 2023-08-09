filename_template = "src/{name}.lambda"
source = r"""
extern crate std;
extern crate io;
use std::*;
use io::*;

pub impure main = _ -> (do ident
    (x -> puts !"Hello, ")
    (x -> puts !"World!\n")
);
""".strip()
