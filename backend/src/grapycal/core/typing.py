import abc
from typing import Any, Type


class GType(abc.ABC):
    @staticmethod
    def from_annotation(annotation: "Type|GType|Any") -> "GType":
        """
        The annotation can be a type expr. Currently type expr in string is not supported.
        """
        if isinstance(annotation, GType):
            return annotation
        if annotation is None or annotation == Any:
            return AnyType
        if isinstance(annotation, type):
            return PlainType(annotation)
        return AnyType

    # we use a >> b (__rshift__) to indicate that a is compatible with b
    # because the symbol looks like plugging a into b
    def __rshift__(self, other: "GType|type|Any"):
        """
        Called when self >> other is evaluated.
        """
        if isinstance(other, GType):
            return isinstance(self, _AnyType) or other._can_accept(self)
        if other is Any:
            return True
        if isinstance(other, type):
            return PlainType(other)._can_accept(self)

    @abc.abstractmethod
    def _can_accept(self, other: "GType") -> bool:
        """
        Check if this type can accept another GType. No need to check if other is AnyType.
        """
        raise NotImplementedError()


class _AnyType(GType):
    def _can_accept(self, other: GType):
        return True


# Instead of creating AnyType everytime, we decide to use a (kind of) singleton
AnyType = _AnyType()


class PlainType(GType):
    def __init__(self, t: type):
        self._type = t

    def _can_accept(self, other: GType):
        return isinstance(other, PlainType) and issubclass(other._type, self._type)

    def __repr__(self):
        return f"PlainType({self._type})"
