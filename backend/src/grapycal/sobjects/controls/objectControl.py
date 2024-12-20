from typing import Any, Callable
from grapycal.extension.utils import ControlInfo
from grapycal.stores import main_store
from objectsync import Topic, StringTopic, IntTopic

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
        self.state = self.add_attribute(
            "state", IntTopic, ObjectControlState.NOT_USING_USER_TEXT, is_stateful=False
        )
        self.label = self.add_attribute("label", StringTopic, label)
        self.text = self.add_attribute("text", StringTopic, self.get_text_from_value())

    def get_state_dict(self):
        return {
            "value": self.value,
        }

    def set_state_dict(self, state):
        self.value = state["value"]

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
        if self.state.get() in [
            ObjectControlState.NOT_USING_USER_TEXT,
            ObjectControlState.USER_TEXT_EVALED,
        ]:
            return self.value
        else:
            # evaluate the user text
            try:
                self.value = eval(self.text.get(), main_store.vars())
                self.state.set(ObjectControlState.USER_TEXT_EVALED)
                return self.value
            except Exception as e:
                raise ValueError(f"Invalid expression {self.text.get()}: {e}")

    def set_from_port(self, value):
        self.state.set(ObjectControlState.NOT_USING_USER_TEXT)
        self.set(value)

    def get_text_from_value(self):
        if isinstance(self.value, str):
            return '"' + self.value + '"'  # add quotes
        return str(self.value)[:100]

    def text_changed(self, text):
        if self.ignore_text_changed:
            return
        if text == "":
            return
        self.state.set(ObjectControlState.USER_TEXT_DIRTY)
        self.value = None  # release memory
        if self.activation_callback:
            self.activation_callback()

    def restore_from(self, old: ControlInfo):
        """
        Default recovery process. If the control class get updated in Grapycal, override this method to customize the recovery process
        for different Grapycal versions.
        """

        if old.attributes["state"] in [
            ObjectControlState.USER_TEXT_DIRTY,
            ObjectControlState.USER_TEXT_EVALED,
        ]:
            self.state.set(ObjectControlState.USER_TEXT_DIRTY)
            self.text.set(old.attributes["text"])
        else:
            self.state.set(ObjectControlState.NOT_USING_USER_TEXT)

        for k, v in old.attributes.items():
            if k in ["state", "text"]:
                continue
            if self.has_attribute(k):
                self.get_attribute(k).set(v)
