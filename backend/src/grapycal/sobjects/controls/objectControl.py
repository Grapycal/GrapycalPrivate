from typing import Any, Callable
from objectsync import Topic
from topicsync.topic import StringTopic

from grapycal.sobjects.controls.control import ValuedControl


class UNSET_:
    def __str__(self):
        return "(unset)"


UNSET = UNSET_()


# TODO: save the value
class ObjectControl(ValuedControl[Any]):
    """
    Used to represent any python object.
    """

    frontend_type = "ObjectControl"

    def build(self, value: Any = UNSET, label: str = ""):
        self.value = value
        self.label = self.add_attribute("label", StringTopic, label)
        self.text = self.add_attribute("text", StringTopic, self.get_text_from_value())

    def set(self, value: bool):
        self.value = value
        self.text.set(self.get_text_from_value())

    def value_ready(self) -> bool:
        return self.value is not UNSET

    def get_value_topic(self) -> Topic:
        raise NotImplementedError("ObjectControl does not have a value topic")

    def take_label(self, label):
        if self.label.get() == "":
            self.label.set(label)
            return True
        return False

    def set_activation_callback(self, callback: Callable[[], None]):
        pass  # The value does not change by the user in the current implementation

    def get(self) -> bool:
        return self.value

    def set_from_port(self, value):
        self.set(value)

    def get_text_from_value(self):
        if self.value is UNSET:
            return "UNSET"
        return str(self.value)[:100]
