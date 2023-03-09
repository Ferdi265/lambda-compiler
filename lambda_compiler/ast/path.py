from __future__ import annotations
from dataclasses import dataclass, field
from typing import *

@dataclass(frozen=True, init=False)
class Path:
    components: Sequence[str]

    def __init__(self, components: Sequence[str]):
        object.__setattr__(self, "components", tuple(components))

    def is_inside(self, other: Path) -> bool:
        if len(self.components) < len(other.components):
            return False

        for i, name in enumerate(other.components):
            if self.components[i] != name:
                return False

        return True

    def __str__(self) -> str:
        return "::".join(self.components)

    def __repr__(self) -> str:
        return str(self)

    def __lt__(self, other: Path) -> bool:
        return tuple(self.components) < tuple(other.components)

    def __truediv__(self, other: Union[Path, str]) -> Path:
        if isinstance(other, Path):
            return Path(tuple(self.components) + tuple(other.components))
        else:
            return Path(tuple(self.components) + (other,))

@dataclass(frozen=True)
class InstancePath:
    path: Path
    id: int

    def __str__(self) -> str:
        return f"{self.path}%{self.id}"

    def __repr__(self) -> str:
        return str(self)

    def __lt__(self, other: InstancePath) -> bool:
        return (self.path, self.id) < (other.path, other.id)

@dataclass(frozen=True)
class ImplementationPath:
    path: Path
    lambda_id: int
    continuation_id: int

    def __str__(self) -> str:
        return f"{self.path}!{self.lambda_id}!{self.continuation_id}"

    def __repr__(self) -> str:
        return str(self)

    def __lt__(self, other: ImplementationPath) -> bool:
        return (self.path, self.lambda_id, self.continuation_id) < (other.path, other.lambda_id, other.continuation_id)
