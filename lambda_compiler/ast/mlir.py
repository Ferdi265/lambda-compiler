from __future__ import annotations
from typing import *
from .path import Path, InstancePath, ImplementationPath
from dataclasses import dataclass

@dataclass
class Statement:
    pass

@dataclass
class ExternCrate(Statement):
    name: str

@dataclass
class Extern(Statement):
    name: str

@dataclass
class Definition(Statement):
    path: Path
    inst: InstancePath
    needs_init: bool
    is_public: bool

@dataclass
class Instance(Statement):
    path: InstancePath
    impl: ImplementationPath
    captures: List[InstancePath]

@dataclass
class Implementation(Statement):
    path: ImplementationPath
    captures: int

@dataclass
class ReturnImplementation(Implementation):
    value: ValueLiteral

@dataclass
class TailCallImplementation(Implementation):
    fn: ValueLiteral
    arg: ValueLiteral

@dataclass
class ContinueCallImplementation(Implementation):
    fn: ValueLiteral
    arg: ValueLiteral
    next: ValueLiteral

@dataclass
class ValueLiteral:
    pass

@dataclass
class CaptureLiteral(ValueLiteral):
    id: int

@dataclass
class ExternLiteral(ValueLiteral):
    name: str

@dataclass
class DefinitionLiteral(ValueLiteral):
    path: Path

@dataclass
class InstanceLiteral(ValueLiteral):
    inst: InstancePath

@dataclass
class ImplementationLiteral(ValueLiteral):
    impl: ImplementationPath
    captures: List[int | InstancePath]
