from __future__ import annotations
from typing import *

T = TypeVar("T")
class OrderedSet(Generic[T]):
    data: List[T]
    def __init__(self, iterable: Optional[Iterable] = None):
        if iterable is None:
            self.data = []
        else:
            self.data = list(iterable)
            self.data.sort()

    def add(self, key: T):
        if key not in self.data:
            self.data.append(key)
            self.data.sort()

    def remove(self, key: Optional[T]):
        if key is not None and key in self.data:
            self.data.remove(key)

    def __copy__(self) -> OrderedSet[T]:
        return OrderedSet(self)

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> Iterator[T]:
        return iter(self.data)

    def __in__(self, key: T) -> bool:
        return key in self.data

    def __and__(self, other: OrderedSet[T]) -> OrderedSet[T]:
        return OrderedSet(key for key in self if key in other)

    def __rand__(self, other: OrderedSet[T]) -> OrderedSet[T]:
        return OrderedSet(key for key in self if key in other)

    def __or__(self, other: OrderedSet[T]) -> OrderedSet[T]:
        return OrderedSet([key for key in self] + [key for key in other])

    def __ror__(self, other: OrderedSet[T]) -> OrderedSet[T]:
        return OrderedSet([key for key in self] + [key for key in other])

    def __iand__(self, other: OrderedSet[T]) -> OrderedSet[T]:
        return self & other

    def __ior__(self, other: OrderedSet[T]) -> OrderedSet[T]:
        return self | other

    def __repr__(self) -> str:
        content = ", ".join(repr(key) for key in self.data)
        return f"OrderedSet({{{content}}})"
