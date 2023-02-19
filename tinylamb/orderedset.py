from __future__ import annotations
from typing import *

T = TypeVar("T")
class OrderedSet(Generic[T]):
    dict: Dict[T, None]
    def __init__(self, iterable: Optional[Iterable] = None):
        if iterable is None:
            self.dict = {}
        else:
            self.dict = {key: None for key in iterable}

    def add(self, item: T):
        if item not in self.dict:
            self.dict[item] = None

    def remove(self, item: T):
        del self.dict[item]

    def __copy__(self) -> OrderedSet[T]:
        return OrderedSet(iter(self))

    def __iter__(self) -> Iterator[T]:
        return iter(self.dict.keys())

    def __in__(self, key: T) -> bool:
        return key in self.dict

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
        content = ", ".join(repr(key) for key in self.dict)
        return f"OrderedSet({{{content}}})"
