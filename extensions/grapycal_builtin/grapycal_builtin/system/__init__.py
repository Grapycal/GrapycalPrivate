import json
import os

import dotenv
from grapycal import InputPort, Node, SourceNode, TextControl
from grapycal.extension_api.decor import func


class EnvironmentVariableNode(SourceNode):
    """

    :inputs:
        - trigger: send in a signal to actively output the environment variable's value
        - set: set the environment variable's value

    :outputs:
        - get: get the environment variable's value

    """

    category = "system"

    def build_node(self):
        super().build_node()
        self.in_port = self.add_in_port("set", 1)
        self.out_port = self.add_out_port("get")
        self.variable_name = self.add_control(TextControl, name="variable_name")
        self.label_topic.set("Environment Variable")
        self.shape_topic.set("simple")
        self.css_classes.append("fit-content")

    def port_activated(self, port: InputPort):
        dotenv.load_dotenv("./.env")
        if port == self.in_port:
            os.environ[self.variable_name.text.get()] = port.get()
        self.flash_running_indicator()

    def task(self):
        if self.variable_name.text.get() not in os.environ:
            self.print_exception(
                f'Environment Variable "{self.variable_name.text.get()}" does not exist'
            )
            return
        value = os.environ[self.variable_name.text.get()]
        self.out_port.push(value)


class ReadJsonNode(Node):
    """
    Read a JSON file and get the data.
    """

    category = "system"

    def build_node(self):
        self.css_classes.append("fit-content")

    @func()
    def data(self, path: str = "data.json"):
        with open(path, "r") as f:
            return json.load(f)


class WriteJsonNode(Node):
    """
    Write data to a JSON file.
    """

    category = "system"

    def build_node(self):
        self.css_classes.append("fit-content")

    @func()
    def done(self, path: str = "data.json", data: dict = {}):
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False)
