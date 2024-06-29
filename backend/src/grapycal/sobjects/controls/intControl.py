from typing import Callable
from objectsync import Topic
from topicsync.topic import IntTopic, StringTopic

from grapycal.sobjects.controls.control import ValuedControl


class IntControl(ValuedControl[int]):
    """ """

    frontend_type = "IntControl"

    def build(self, value: int = 0, label: str = ""):
        self.value = self.add_attribute("value", IntTopic, value)
        self.label = self.add_attribute("label", StringTopic, label)
        self.on_value_set = self.value.on_set

    def set(self, value: int):
        self.value.set(value)

    def value_ready(self) -> int:
        return True

    def get_value_topic(self) -> Topic:
        return self.value

    def take_label(self, label):
        if self.label.get() == "":
            self.label.set(label)
            return True
        return False

    def set_activation_callback(self, callback: Callable[[], None]):
        self.value.on_set += callback

    def get(self) -> int:
        return self.value.get()

    def set_with_value_from_edge(self, value):
        assert isinstance(value, int), f"Expected int, got {type(value)}"
        self.set(value)
