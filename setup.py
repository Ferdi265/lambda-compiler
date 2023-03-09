from setuptools import setup

with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

with open("lambda_compiler/version.py", "r") as f:
    exec(f.read(), globals())

setup(
    name = "lambda_compiler",
    description = "a Lambda Calculus to LLVM IR compiler",
    version = __version__,
    author = "Ferdinand Bachmann",
    author_email = "theferdi265@gmail.com",
    packages = ["lambda_compiler", "lambda_compiler.cli"],
    entry_points = {
        "console_scripts": [
            "lambda-lang2deps=lambda_compiler.cli.lang2deps:main",
            "lambda-lang2hlir=lambda_compiler.cli.lang2hlir:main",
            "lambda-hlir2hlis=lambda_compiler.cli.hlir2hlis:main",
            "lambda-hlir2mlir=lambda_compiler.cli.hlir2mlir:main",
            "lambda-mlir2opt=lambda_compiler.cli.mlir2opt:main",
            "lambda-mlir2llir=lambda_compiler.cli.mlir2llir:main",
            "lambda-mlir2main=lambda_compiler.cli.mlir2main:main",
        ]
    },
    package_data = {
        "lambda_compiler": ["py.typed"]
    },
    python_requires = ">=3.10",
    install_requires = requirements
)
