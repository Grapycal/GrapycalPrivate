from typing import Any, Callable, List, TypeVar

T = TypeVar("T")


def as_type(x, t: type[T]) -> T:
    assert isinstance(x, t)
    return x


class Action:
    """
    A hub for callbacks
    """

    def __init__(self):
        self.callbacks: List[Callable] = []

    def __add__(self, callback: Callable):
        """
        Temporary backward compatibility. To be removed.
        """
        self.callbacks.append(callback)
        return self

    def __sub__(self, callback: Callable):
        """
        Temporary backward compatibility. To be removed.
        """
        self.callbacks.remove(callback)
        return self

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """Call each callback in the action with the given arguments."""
        returns = []
        for callback in self.callbacks:
            returns.append(callback(*args, **kwargs))
        return returns


class SemVer:
    """
    Parse and compare semantic version strings.
    0.15.0-a.5+dev -> major: 0, minor: 15, patch: 0, pre: a, build: 5
    """

    def __init__(self, version: str):
        self.version = version
        if "+" in version:
            rest, self.build = version.split("+")
        else:
            rest = version
            self.build = None
        if "-" in rest:
            num, rest = rest.split("-", 1)
            self.pre = rest
        else:
            self.pre = None
            num = rest
        self.major, self.minor, self.patch = map(int, num.split("."))

    def __lt__(self, other: "SemVer") -> bool:
        if self.major < other.major:
            return True
        if self.major > other.major:
            return False
        if self.minor < other.minor:
            return True
        if self.minor > other.minor:
            return False
        if self.patch < other.patch:
            return True
        if self.patch > other.patch:
            return False

        if self.pre == other.pre:
            return False
        if self.pre is None:
            return False
        if other.pre is None:
            return True
        return self.pre < other.pre

    def __eq__(self, other: "SemVer") -> bool:
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __str__(self):
        return f"major: {self.major}, minor: {self.minor}, patch: {self.patch}, pre: {self.pre}, build: {self.build}"
