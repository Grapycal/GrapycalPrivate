from topicsync.topic import GenericTopic, StringTopic

from grapycal.sobjects.controls.control import Control


class ToggleControl(Control):
    """ """

    frontend_type = "ToggleControl"

    def build(self, value: bool = False, label: str = ""):
        self.value = self.add_attribute("value", GenericTopic[bool], value)
        self.label = self.add_attribute("label", StringTopic, label)
        self.on_value_set = self.value.on_set

    def set(self, value: bool):
        self.value.set(value)