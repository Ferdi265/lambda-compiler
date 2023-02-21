# Lambda-Compiler

A Lambda Calculus to LLVM IR compiler

## Installation

- run `pip install git+https://github.com/Ferdi265/lambda-compiler` to install
- run `pip install --editable .` for a development install

## Examples

- a few example programs are found in the `examples/` subdirectory

## Compilation

Compilation is done in four steps:

- collect a whole Lambda crate into one file and resolve dependencies (`lambda-lambda2hlir`, not yet implemented)
- compile Lambda calculus expressions to simple returns, tail calls, and calls, with explicit captures (`lambda-hlir2mlir`)
- translate the resulting intermediate language to LLVM IR (`lambda-mlir2llir`) and generate a main function (`lambda-llir2main`)
- compile the resulting LLVM IR together with the runtime and external IO routines into a program (`clang`)

## Language

Lambda is an eagerly evaluated lambda calculus.
