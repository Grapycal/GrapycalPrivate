import abc


class GType(abc.ABC):
    # we use a >> b (__rshift__) to indicate that a is compatible with b
    # because the symbol looks like plugging a into b
    def __rshift__(self, other: 'GType'):
        return isinstance(self, _AnyType) or other._can_accept(self)

    @abc.abstractmethod
    def _can_accept(self, other: 'GType') -> bool:
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