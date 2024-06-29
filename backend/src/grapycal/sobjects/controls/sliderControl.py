from typing import Callable
from objectsync import DictTopic, FloatTopic, StringTopic, Topic

from grapycal.sobjects.controls.control import ValuedControl


class SliderControl(ValuedControl[None]):
    """
    To add a slider control to a node, use the following code in the node:
    ```python
    self.add_control(SliderControl, label='slider', value=0, min=0, max=1, step=0.01, int_mode=False)
    ```
    """

    frontend_type = "SliderControl"

    def build(
        self,
        label: str = "",
        value: float = 0,
        min: float = 0,
        max: float = 1,
        step: float = 0.01,
        int_mode: bool = False,
    ):
        self.label = self.add_attribute("label", StringTopic, label)
        self.value = self.add_attribute("value", FloatTopic, value)
        if int_mode:
            min = int(min)
            max = int(max)
            step = int(step)
            value = int(value)
        self.config = self.add_attribute(
            "config",
            DictTopic,
            {"min": min, "max": max, "step": step, "int_mode": int_mode},
            is_stateful=False,
        )

    def init(self):
        self.on_set = self.value.on_set

    # def set_activation_callback(self, callback):
    #     self.on_set += callback

    def get(self) -> int | float:
        if self.config["int_mode"]:
            return int(self.value.get())
        return self.value.get()

    def get_value_topic(self) -> Topic:
        return self.value

    def get_int(self) -> int:
        return int(self.value.get())

    def set(self, value: float):
        if self.config["int_mode"]:
            value = int(value)

        if value < self.config["min"]:
            value = self.config["min"]

        if value > self.config["max"]:
            value = self.config["max"]

        self.value.set(value)

    def value_ready(self) -> bool:
        return True

    def take_label(self, label) -> bool:
        if self.label.get() == "":
            self.label.set(label)
            return True
        return False

    def set_activation_callback(self, callback: Callable[[], None]):
        self.on_set += callback

    def set_min(self, min: float):
        self.config["min"] = min

    def set_max(self, max: float):
        self.config["max"] = max

    def set_step(self, step: float):
        self.config["step"] = step

    def set_integer_mode(self):
        self.config["int_mode"] = True
        self.config["min"] = int(self.config["min"])
        self.config["max"] = int(self.config["max"])
        self.config["step"] = int(self.config["step"])

    def set_float_mode(self):
        self.config["int_mode"] = False

    def set_with_value_from_edge(self, value):
        assert isinstance(
            value, (int, float)
        ), f"Expected int or float, got {type(value)}"
        self.set(value)
