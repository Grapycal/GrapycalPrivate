from typing import Any, Callable
from grapycal.stores import main_store
from objectsync import Topic, StringTopic

from grapycal.sobjects.controls.control import ValuedControl


class ObjectControlState:
    USER_TEXT_DIRTY = 1
    USER_TEXT_EVALED = 2
    NOT_USING_USER_TEXT = 3


# TODO: save the value
class ObjectControl(ValuedControl[Any]):
    """
    Used to represent any python object.
    """

    frontend_type = "ObjectControl"

    def build(self, value: Any = None, label: str = ""):
        self.value = value
        self.state = ObjectControlState.NOT_USING_USER_TEXT
        self.label = self.add_attribute("label", StringTopic, label)
        self.text = self.add_attribute("text", StringTopic, self.get_text_from_value())

    def get_state_dict(self):
        return {
            "value": self.value,
            "state": self.state,
        }

    def set_state_dict(self, state):
        self.value = state["value"]
        self.state = state["state"]

    def init(self):
        self.activation_callback = None
        self.text.on_set += self.text_changed
        self.ignore_text_changed = False

    def set(self, value: bool):
        self.value = value
        try:
            self.ignore_text_changed = True
            self.text.set(self.get_text_from_value())
        finally:
            self.ignore_text_changed = False

    def value_ready(self) -> bool:
        return True

    def get_value_topic(self) -> Topic:
        return self.text

    def take_label(self, label):
        if self.label.get() == "":
            self.label.set(label)
            return True
        return False

    def set_activation_callback(self, callback: Callable[[], None]):
        self.activation_callback = callback

    def get(self):
        if self.state in [
            ObjectControlState.NOT_USING_USER_TEXT,
            ObjectControlState.USER_TEXT_EVALED,
        ]:
            return self.value
        else:
            # evaluate the user text
            try:
                self.value = eval(self.text.get(), main_store.vars())
                self.state = ObjectControlState.USER_TEXT_EVALED
                return self.value
            except Exception as e:
                raise ValueError(f"Invalid expression {self.text.get()}: {e}")

    def set_from_port(self, value):
        self.state = ObjectControlState.NOT_USING_USER_TEXT
        self.set(value)

    def get_text_from_value(self):
        return str(self.value)[:100]

    def text_changed(self, text):
        if self.ignore_text_changed:
            return
        if text == "":
            return
        self.state = ObjectControlState.USER_TEXT_DIRTY
        self.value = None  # release memory
        if self.activation_callback:
            self.activation_callback()
