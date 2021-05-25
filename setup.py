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
    packages = ["tinylamb"],
    entry_points = {},
    python_requires = ">=3.10",
    install_requires = requirements
)
