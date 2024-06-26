# Lambda-Compiler

A Lambda Calculus to LLVM IR compiler

## Installation

- run `pipx install git+https://github.com/Ferdi265/lambda-compiler` to install
- run `pipx install --editable .` for a development install

`pipx` is a modern replacement for installing CLI applications with `pip`
directly, since `pip` now by default forbids installing applications outside a
virtualenv on most distros. You can use `pip` as well, but `pipx` is
recommended.

## Examples

- a few example programs are found in the `examples/` subdirectory
- you can create a new project by running `lambda-mkmake myproject` in a new folder

## Compilation

Compilation is done in five steps:

- collect GNU Make dependency information for a Lambda crate (`lambda-lang2deps`)
- collect a whole Lambda crate into one file, resolve names and macros (`lambda-lang2hlir`)
- compile Lambda calculus expressions to simple returns, tail calls, and calls, with explicit captures (`lambda-hlir2mlir`)
- translate the resulting intermediate language to LLVM IR (`lambda-mlir2llir`) and generate a main function (`lambda-mlir2main`)
- compile the resulting LLVM IR together with the runtime and external IO routines into a program (`clang`)

## Language

Lambda is an eagerly evaluated lambda calculus.

- Function Application: `func arg1 arg2` is equivalent to `(func(arg1))(arg2)` in Python
- Lambda Construction: `func arg -> body` is equivalent to `func(lambda arg: body)` in Python
- Parentheses can be used to adjust precedence:
    - `func arg -> body arg2` is equivalent to `func(lambda arg: body(arg2))` in Python
    - `func (arg -> body) arg2` is equivalent to `(func(lambda arg: body))(arg2)` in Python
- Macros are prefixed by `!` and expand to regular calls to functions defined in `std.lambda`:
    - `!"string"` expands to a call to `(std::list_n ...)` constructing a list
      of numbers representing the UTF-8 bytes of the string
    - `!42` expands to a call to `(std::dec2 ...)` or `(std::dec3 ...)` to
      construct a number object. Number literals greater than 999 are currently
      not supported.

A Lambda program is a list of definitions that can only refer to previous
definitions (not to themselves). This means one has to use a fixed point
combinator such as the y combinator to create recursive functions.

### Example:

```
true = a -> b -> a;
false = a -> b -> b;

not = a -> a false true;
```
