from __future__ import annotations
from .mlir import *

@dataclass
class LinkedDefinition(Statement):
    path: Path
    inst: LinkedInstance
    needs_init: bool
    is_public: bool

@dataclass
class LinkedInstance(Statement):
    path: InstancePath
    impl: Implementation
    captures: List[LinkedInstance]

@dataclass
class LinkedDefinitionLiteral(ValueLiteral):
    defi: LinkedDefinition

@dataclass
class LinkedInstanceLiteral(ValueLiteral):
    inst: LinkedInstance

@dataclass
class LinkedImplementationLiteral(ValueLiteral):
    impl: Implementation
    captures: List[int | LinkedInstance]
