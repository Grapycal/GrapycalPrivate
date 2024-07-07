from grapycal.sobjects.controls.control import ValuedControl
from objectsync import StringTopic, EventTopic


class TriggerControl(ValuedControl[None]):
    """
    Used by DecorTrait. Represents that to run a node as a task.
    """

    frontend_type = "TriggerControl"

    def build(self, label: str = ""):
        self.label = self.add_attribute("label", StringTopic, label, is_stateful=False)
        self._click = self.add_attribute("click", EventTopic, is_stateful=False)

    def init(self):
        self.on_click = self._click.on_emit

    def set_activation_callback(self, callback):
        self.on_click += callback

    def get(self) -> None:
        return None

    def value_ready(self) -> bool:
        return True

    def get_value_topic(self):
        return self._click

    def take_label(self, label) -> bool:
        if self.label.get() == "":
            self.label.set(label)
            return True
        return False
