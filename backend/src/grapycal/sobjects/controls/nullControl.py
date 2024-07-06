from grapycal.sobjects.controls.control import ValuedControl


class NullControl(ValuedControl):
    def get(self):
        raise Exception("Data not available")

    def value_ready(self) -> bool:
        return False

    def get_value_topic(self):
        raise Exception("NullControl does not have a value topic")

    def set_activation_callback(self, callback):
        pass
