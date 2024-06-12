from contextlib import contextmanager
import sys
from typing import TYPE_CHECKING, Callable, Dict, List
from objectsync import Topic
import importlib.util


class HasLibChecker:
    def __init__(self) -> None:
        self._has_lib: Dict[str, bool] = {}

    def has_lib(self, lib: str) -> bool:
        """
        Checks if a library is available without importing it
        """
        if lib in self._has_lib:
            return self._has_lib[lib]
        self._has_lib[lib] = importlib.util.find_spec(lib) is not None
        return self._has_lib[lib]

    def imported(self, lib: str) -> bool:
        """
        Checks if a library is already imported
        """
        return lib in sys.modules


has_lib_checker = HasLibChecker()


class Bus:
    """
    Syncronizes all topics attached to it
    """

    @contextmanager
    def lock(self):
        self._lock = True
        yield
        self._lock = False

    def __init__(self):
        self._topics: List[Topic] = []
        self._callbacks: Dict[Topic, Callable] = {}
        self._lock = False

    def add(self, topic: Topic):
        if len(self._topics):
            topic.set(self._topics[0].get())
        self._topics.append(topic)
        callback = lambda value: self._change(topic, value)
        topic.on_set += callback
        self._callbacks[topic] = callback

    def __add__(self, topic: Topic):
        self.add(topic)
        return self

    def remove(self, topic: Topic):
        self._topics.remove(topic)
        topic.on_set -= self._callbacks[topic]
        del self._callbacks[topic]

    def __sub__(self, topic: Topic):
        self.remove(topic)
        return self

    def _change(self, source: Topic, value):
        if self._lock:
            return
        with self.lock():
            for topic in self._topics:
                if topic.get() == value or topic == source:
                    continue
                topic.set(value)

    def __len__(self):
        return len(self._topics)


if TYPE_CHECKING:
    import numpy as np


def to_numpy(data) -> "np.ndarray":
    """
    Converts data to numpy array
    """
    import numpy as np

    if isinstance(data, list):
        return np.array(data)
    try:
        import torch
    except ImportError:
        return data
    if isinstance(data, torch.Tensor):
        return data.cpu().detach().numpy()
    return data


def is_numpy_array(data) -> bool:
    """
    Checks if data is a numpy array
    """
    if not has_lib_checker.imported("numpy"):
        return False
    import numpy as np

    return isinstance(data, np.ndarray)


def is_torch_tensor(data) -> bool:
    """
    Checks if data is a torch tensor
    """
    if not has_lib_checker.imported(
        "torch"
    ):  # there cannot be a torch.Tensor without torch
        return False
    import torch

    return isinstance(data, torch.Tensor)
