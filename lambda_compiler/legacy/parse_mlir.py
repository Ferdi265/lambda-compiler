from __future__ import annotations
from typing import *

from .parse import *
from .continuations import *

@dataclass(frozen=True)
class InstancePath:
    path: Path
    inst_id: int

    def __lt__(self, other: InstancePath) -> bool:
        return (self.path, self.inst_id) < (other.path, other.inst_id)

    def __str__(self) -> str:
        return f"{self.path}%{self.inst_id}"

    def __repr__(self) -> str:
        return str(self)

@dataclass(frozen=True)
class ImplementationPath:
    path: Path
    lambda_id: int
    continuation_id: int

    def __lt__(self, other: ImplementationPath) -> bool:
        return (self.path, self.lambda_id, self.continuation_id) < (other.path, other.lambda_id, other.continuation_id)

    def __str__(self) -> str:
        return f"{self.path}!{self.lambda_id}!{self.continuation_id}"

    def __repr__(self) -> str:
        return str(self)

@dataclass
class MInstanceDefinition(Statement):
    path: Path
    inst: InstancePath
    needs_init: bool
    is_public: bool

@dataclass
class MInstance(Statement):
    path: InstancePath
    impl: ImplementationPath
    captures: List[InstancePath]

@dataclass
class MImplementation(Statement):
    path: ImplementationPath
    captures: List[int]

@dataclass
class MReturnImplementation(MImplementation):
    value: ValueLiteral

@dataclass
class MTailCallImplementation(MImplementation):
    fn: ValueLiteral
    arg: ValueLiteral

@dataclass
class MContinueCallImplementation(MImplementation):
    fn: ValueLiteral
    arg: ValueLiteral
    next: ValueLiteral

@dataclass
class MInstanceLiteral(ValueLiteral):
    inst: InstancePath

@dataclass
class MImplementationLiteral(ValueLiteral):
    impl: MImplementation
