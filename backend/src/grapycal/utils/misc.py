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
    """

    def __init__(self, version: str):
        self.version = version
        self.major, self.minor, self.patch_pre_build = version.split(".")
        if "+" in self.patch_pre_build:
            self.patch_pre, self.build = self.patch_pre_build.split("+")
        else:
            self.patch_pre = self.patch_pre_build
            self.build = None
        if "-" in self.patch_pre:
            self.patch, self.pre = self.patch_pre.split("-")
        else:
            self.patch = self.patch_pre
            self.pre = None

    def __lt__(self, other: "SemVer") -> bool:
        if self.major < other.major:
            return True
        if self.minor < other.minor:
            return True
        if self.patch < other.patch:
            return True
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
