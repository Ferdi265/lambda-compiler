from typing import *
from pathlib import Path
from lambda_compiler.version import __version__
from lambda_compiler import bundled_files as bf
import argparse

def parse_args() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(
        description = "create a GNU Make project for compiling Lamda programs"
    )

    ap.add_argument("name", help = "the crate name for the Lambda project")
    ap.add_argument("-v", "--version", action = "store_true", default=False, help = "print current version and exit")

    return ap, ap.parse_args()

def write_file(name: str, content: str):
    path = Path(name)
    path.parent.mkdir(exist_ok = True, parents = True)
    with open(path, "w") as f:
        f.write(content + "\n")

def main():
    ap, args = parse_args()

    if args.version:
        print(f"{ap.prog} {lambda_compiler.__version__}")
        return

    name = args.name
    if name is None:
        ap.print_help()
        return

    write_file(bf.makefile.filename, bf.makefile.source_template.format(name = name))
    write_file(bf.crate_lambda.filename_template.format(name = name), bf.crate_lambda.source)
    write_file(bf.std_lambda.filename, bf.std_lambda.source)
    write_file(bf.io_lambda.filename, bf.io_lambda.source)
    write_file(bf.io_c.filename, bf.io_c.source)
    write_file(bf.runtime_h.filename, bf.runtime_h.source)
    write_file(bf.runtime_c.filename, bf.runtime_c.source)

if __name__ == "__main__":
    main()
