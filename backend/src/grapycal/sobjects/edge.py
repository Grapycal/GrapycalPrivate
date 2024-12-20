from typing import Any

from objectsync import ObjTopic, SObject, StringTopic
from objectsync.sobject import SObjectSerialized

from grapycal.sobjects.port import InputPort, OutputPort, Port

TRY_IMPORT_CALLED = False


def try_import():
    global HAS_TORCH, HAS_NUMPY, torch, np, TRY_IMPORT_CALLED
    TRY_IMPORT_CALLED = True
    try:
        import torch

        HAS_TORCH = True
    except ImportError:
        HAS_TORCH = False

    try:
        import numpy as np

        HAS_NUMPY = True
    except ImportError:
        HAS_NUMPY = False


class Edge(SObject):
    frontend_type = "Edge"

    def build(self, tail: OutputPort | None = None, head: InputPort | None = None):
        self.tail = self.add_attribute("tail", ObjTopic[OutputPort], tail)
        self.head = self.add_attribute("head", ObjTopic[InputPort], head)
        self.label = self.add_attribute("label", StringTopic, is_stateful=False)

    def init(self):
        if not TRY_IMPORT_CALLED:
            try_import()
        self._data = None
        self._activated = False
        self._data_ready = False
        self.reaquirable = False

        self.tail.on_set2 += self.on_tail_set
        self.head.on_set2 += self.on_head_set

        self.on_tail_set(None, self.tail.get())
        self.on_head_set(None, self.head.get())

        parent = self.get_parent()
        from grapycal.sobjects.editor import Editor

        assert isinstance(parent, Editor)
        self.editor = parent

    def on_tail_set(self, old_tail: Port | None, new_tail: Port | None):
        if old_tail:
            old_tail.remove_edge(self)
        if new_tail is None:
            self.remove()
            raise Exception(f"{self} tail cannot be None")
        if new_tail:
            new_tail.add_edge(self)
        self.label.set("")

    def on_head_set(self, old_head: Port | None, new_head: InputPort | None):
        if old_head:
            old_head.remove_edge(self)
        if new_head is None:
            self.remove()
            raise Exception(f"{self} head cannot be None")
        if new_head:
            new_head.add_edge(self)
            if self._activated:
                new_head.node.edge_activated(self, new_head)

    def destroy(self) -> SObjectSerialized:
        if self.tail.get():
            self.tail.get().remove_edge(self)
        if self.head.get():
            self.head.get().remove_edge(self)

        if hasattr(self, "editor"):
            self.editor.is_running_manager.set_running(self, False)
        return super().destroy()

    def get(self) -> Any:
        if not self._data_ready:
            raise Exception("Data not available")
        self._activated = False
        temp = self._data
        if not self.reaquirable:
            self._data_ready = False

            self.editor.is_running_manager.set_running(self, False)
            self._data = None  # reloase memory
        return temp

    def peek(self) -> Any:
        if not self._data_ready:
            raise Exception("Data not available")
        return self._data

    def push(self, data, label: str | None = None):
        """
        Send data into the edge and activate it. If the edge is already activated, the data will overwrite the old data.
        The head node can get the data with Edge.get() method.
        """
        self._data = data
        self._activated = True
        self._data_ready = True
        with self._server.record(
            allow_reentry=True
        ):  # aquire a lock to prevent calling set while destroying
            if self.is_destroyed():
                return
            self.editor.is_running_manager.set_running(self, True)
        if label:
            self.label.set(label)
        else:
            label = ""
            if HAS_TORCH and isinstance(data, torch.Tensor):
                label = f"T{list(data.shape)}" if list(data.shape) != [] else "scalar"
            elif HAS_NUMPY and isinstance(data, np.ndarray):
                label = f"N{list(data.shape)}" if list(data.shape) != [] else "scalar"
            elif isinstance(data, list):
                label = f"[{len(data)}]"

            self.label.set(label)

        head = self.head.get()
        if head:
            head.activated_by_edge(self)

        self._activated = False

    def clear(self):
        if self.is_data_ready():
            self.get()  # clear the data

    def set_label(self, label):
        self.label.set(label)

    def is_activated(self):
        return self._activated

    def is_data_ready(self):
        return self._data_ready

    def get_tail(self):
        tail = self.tail.get()
        assert tail is not None
        return tail

    def get_head(self):
        head = self.head.get()
        assert head is not None
        return head
