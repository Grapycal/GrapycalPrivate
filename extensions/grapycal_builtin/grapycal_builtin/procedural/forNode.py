from typing import Iterable

from grapycal import Node
from grapycal.extension_api.decor import param
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import InputPort
from grapycal.sobjects.sourceNode import SourceNode
from topicsync.topic import StringTopic


class ForNode(Node):
    """
    Iterate through an iterable object such as a list or a range.

    Each item is pushed to the ``item`` port in order.

    Equivalent to a for loop in Python.
    """

    category = "procedural"

    def build_node(self):
        super().build_node()
        self.iterable_port = self.add_in_port("iterable")
        self.item_port = self.add_out_port("item")
        self.label_topic.set("For")
        self.shape_topic.set("simple")
        self.shuffle = self.add_attribute(
            "shuffle",
            StringTopic,
            editor_type="options",
            init_value="No",
            options=["No", "Yes"],
        )

    def init_node(self):
        self.iterator: Iterable | None = None

    def edge_activated(self, edge: Edge, port: InputPort):
        self.run(self.task)

    def task(self):
        iterable = self.iterable_port.get()
        if self.shuffle.get() == "Yes":
            import random

            iterable = list(iterable)
            random.shuffle(iterable)
        self.iterator = iter(iterable)  # type: ignore
        self.run(self.next, to_queue=False)

    def next(self):
        if self.iterator is None:
            return
        try:
            item = next(self.iterator)  # type: ignore
        except StopIteration:
            return
        self.run(self.next, to_queue=False)
        for edge in self.item_port.edges:
            edge.push(item)

    def icon_clicked(self):
        self.iterator = None
        self.print("Iteration interrupted")


class RepeatNode(SourceNode):
    """
    𝄆 Repeatly push numbers from 0 to ``times``-1 to the ``item`` port. 𝄇

    Shortcut for ``For`` node with ``range`` as iterable.

    Equivalent to `for i in range(times):` in Python.
    """

    category = "procedural"

    def build_node(self):
        super().build_node()
        self.item_port = self.add_out_port("item")
        self.label_topic.set("For")
        self.shape_topic.set("simple")

    def init_node(self):
        super().init_node()
        self.iterator: Iterable | None = None

    @param()
    def param(self, times: int = 10):
        """
        Number of times to repeat.
        """
        self.times = times
        self.label_topic.set(f"⟳ Repeat {self.times}")

    def edge_activated(self, edge: Edge, port: InputPort):
        self.run(self.task)

    def task(self):
        self.iterator = iter(range(self.times))
        self.run(self.next, to_queue=False)

    def next(self):
        if self.iterator is None:
            return
        try:
            item = next(self.iterator)  # type: ignore
        except StopIteration:
            self.iterator = None
            return
        self.run(self.next, to_queue=False)
        for edge in self.item_port.edges:
            edge.push(item)

    def icon_clicked(self):
        if self.iterator is None:
            super().icon_clicked()
        else:
            self.iterator = None
            self.print("Iteration interrupted")
