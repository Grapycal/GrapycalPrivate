import abc


class GType(abc.ABC):
    # we use a >> b (__rshift__) to indicate that a is compatible with b
    # because the symbol looks like plugging a into b
    def __rshift__(self, other):
        return isinstance(other, _AnyType) or self._match_typed(other)

    @abc.abstractmethod
    def _match_typed(self, other):
        raise NotImplementedError()


class _AnyType(GType):
    def _match_typed(self, other):
        return True

# Instead of creating AnyType everytime, we decide to use a (kind of) singleton
AnyType = _AnyType()


class PlainType(GType):
    def __init__(self, t: type):
        self.type = t

    def _match_typed(self, other):
        return isinstance(other, PlainType) and self.type == other.type
