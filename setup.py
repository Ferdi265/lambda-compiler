from setuptools import setup

with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

with open("tinylamb/version.py", "r") as f:
    exec(f.read(), globals())

setup(
    name = "tinylamb",
    description = "tiny partial compiler for a subset of the Lambda language",
    version = __version__,
    author = "Ferdinand Bachmann",
    author_email = "theferdi265@gmail.com",
    packages = ["tinylamb", "tinylamb.cli"],
    entry_points = {
        "console_scripts": [
            "lambda-hlir2mlir=tinylamb.cli.hlir2mlir:main",
            "lambda-mlir2llir=tinylamb.cli.mlir2llir:main",
        ]
    },
    package_data = {
        "tinylamb": ["py.typed"]
    },
    python_requires = ">=3.10",
    install_requires = requirements
)
