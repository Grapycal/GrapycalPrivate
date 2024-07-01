from typing import Callable
from objectsync import Topic
from topicsync.topic import FloatTopic, StringTopic

from grapycal.sobjects.controls.control import ValuedControl


class FloatControl(ValuedControl[float]):
    """ """

    frontend_type = "FloatControl"

    def build(self, value: float = 0, label: str = ""):
        self.value = self.add_attribute("value", FloatTopic, value)
        self.label = self.add_attribute("label", StringTopic, label)
        self.on_value_set = self.value.on_set

    def set(self, value: float):
        self.value.set(value)

    def value_ready(self) -> float:
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

    def get(self) -> float:
        return self.value.get()

    def set_from_port(self, value):
        assert isinstance(value, float), f"Expected float, got {type(value)}"
        self.set(value)
