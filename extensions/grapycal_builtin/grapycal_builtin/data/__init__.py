import re

from grapycal import ListTopic, StringTopic
from grapycal.extension_api.trait import (
    Trait,
    InputsTrait,
    OutputsTrait,
)
from grapycal.extension_api.utils import is_torch_tensor
from grapycal.sobjects.controls import TextControl
from grapycal.sobjects.controls.buttonControl import ButtonControl
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.node import Node, deprecated
from grapycal.sobjects.port import InputPort
from grapycal.sobjects.sourceNode import SourceNode
from topicsync.topic import FloatTopic, GenericTopic, IntTopic
from grapycal.extension_api.decor import func, param


class VariableNode(SourceNode):
    """

    VariableNode stores a variable in the workspace. It can be used to store data for later use.

    :inputs:
        - trigger: to output the variable's value to the `get` port
        - set: set the variable's value

    :outputs:
        - get: get the variable's value

    """

    category = "data"

    def build_node(self):
        super().build_node()
        self.in_port = self.add_in_port("set", 1)
        self.out_port = self.add_out_port("get")
        self.variable_name = self.add_control(TextControl, name="variable_name")
        self.label_topic.set("Variable")
        self.shape_topic.set("simple")
        self.css_classes.append("fit-content")

    def init_node(self):
        super().init_node()
        self.value = None
        self.has_value = False

    def edge_activated(self, edge: Edge, port: InputPort):
        if port == self.in_port:
            self.get_vars()[self.variable_name.text.get()] = edge.get()
        self.flash_running_indicator()

    def task(self):
        if self.variable_name.text.get() not in self.get_vars():
            self.print_exception(
                f'Variable "{self.variable_name.text.get()}" does not exist'
            )
            return
        self.value = self.get_vars()[self.variable_name.text.get()]
        self.has_value = True
        for edge in self.out_port.edges:
            edge.push(self.value)


class GetItemNode(Node):
    """
    Get items from a list, dictionary, array, tensor, etc. by specifying the keys.
    Note that the keys must be valid Python expressions. If the key is a string, it must be enclosed in quotes.
    To omit quotes for string indicies, use GetItemStringIndexNode instead.
    """

    category = "data"

    def build_node(self):
        self.in_port = self.add_in_port("data structure", 1)
        self.keys = self.add_attribute("keys", ListTopic, editor_type="list")

        if not self.is_new:
            for key in self.keys:
                self.add_out_port(key)

    def init_node(self):
        self.keys.on_insert.add_auto(self.add_key)
        self.keys.on_pop.add_auto(self.remove_key)

    def add_key(self, key, position):
        self.add_out_port(key)

    def remove_key(self, key, position):
        self.remove_out_port(key)

    def edge_activated(self, edge: Edge, port: InputPort):
        self.run(self.task, background=False)

    def task(self):
        data = self.in_port.get()
        for out_port in self.out_ports:
            key = out_port.name.get()
            out_port.push(eval(f"_data[{key}]", self.get_vars(), {"_data": data}))


class GetItemStringIndexNode(Node):
    """
    Get items from a data structure using string indices. Quotes are not required for the keys.
    """

    category = "data"

    def build_node(self):
        self.in_port = self.add_in_port("data structure", 1)
        self.keys = self.add_attribute("keys", ListTopic, editor_type="list")

        if not self.is_new:
            for key in self.keys:
                self.add_out_port(key)

    def init_node(self):
        self.keys.on_insert.add_auto(self.add_key)
        self.keys.on_pop.add_auto(self.remove_key)

    def add_key(self, key, position):
        self.add_out_port(key)

    def remove_key(self, key, position):
        self.remove_out_port(key)

    def edge_activated(self, edge: Edge, port: InputPort):
        self.run(self.task, background=False)

    def task(self):
        data = self.in_port.get()
        for out_port in self.out_ports:
            key = out_port.name.get()
            out_port.push(data[key])


class BuildStringNode(Node):
    category = "data"

    def define_traits(self):
        self.ins = InputsTrait(
            ins=[""],
            expose_attr=True,
            on_all_ready=self.task,
            enable_add_button=True,
        )
        self.outs = OutputsTrait(outs=["result"])
        return [self.ins, self.outs]

    def task(self, **kwargs):
        result = ""
        for value in kwargs.values():
            result += str(value) if not isinstance(value, str) else value
        self.outs.push("result", result)


class BuildDictNode(Node):
    category = "data"

    def define_traits(self):
        self.ins = InputsTrait(expose_attr=True, on_all_ready=self.task)
        self.outs = OutputsTrait(outs=["result"])
        return [self.ins, self.outs]

    def task(self, **kwargs):
        self.outs.push("result", kwargs)


class RegexFindAllNode(Node):
    """
    ReFindAllNode is used to find all occurrences of a regular expression in a string.

    :inputs:
        - string: the string to be searched
        - pattern: the regular expression pattern

    :outputs:
        - matches: a list of all matches
    """

    category = "data"

    def build_node(self):
        self.css_classes.append("fit-content")

    @func(background=False)
    def matches(self, string: str = "123ouo456", pattern: str = "[0-9]+") -> list:
        return re.findall(pattern, string)


class ZipNode(Node):
    """
    ZipNode is used to combine multiple lists into a single list.

    :inputs:
        - list1: the first list
        - list2: the second list
        etc.

    :outputs:
        - list: the combined list

    :param required_length: the required length of all input lists. If set to -1, nothing will be checked. If set to a positive integer, all input lists must have that length, otherwise an error will be raised.
    """

    category = "data"

    @param()
    def param(self, required_length: int = -1):
        self.required_length = required_length

    def build_node(self):
        self.out_port = self.add_out_port("output")
        self.label_topic.set("Zip")
        self.shape_topic.set("normal")
        self.items = self.add_attribute("items", ListTopic, editor_type="list")
        self.add_button = self.add_control(ButtonControl, name="add", label="Add")

        if not self.is_new:
            for item in self.items:
                self.add_item(item, -1)
        else:
            self.items.insert("1")

    def init_node(self):
        self.items.on_insert.add_auto(self.add_item)
        self.items.on_pop.add_auto(self.remove_item)
        self.add_button.on_click.add_auto(self.add_pressed)

    def add_item(self, item, position):
        self.add_in_port(item, 1, display_name="")  # TODO: add control

    def remove_item(self, item, position):
        self.remove_in_port(item)

    def add_pressed(self):
        new_item = 0
        for item in self.items:
            if re.match(r"[0-9]+", item):
                new_item = max(new_item, int(item))
        new_item += 1
        self.items.insert(str(new_item))

    def icon_clicked(self):
        self.task()

    def edge_activated(self, edge: Edge, port: InputPort):
        self.task()

    def task(self):
        if not all([port.is_all_ready() for port in self.in_ports]):
            return
        inputs = []
        for item in self.items:
            inputs.append(self.get_in_port(item).get())

        if self.required_length != -1:
            for input_list in inputs:
                if len(input_list) != self.required_length:
                    self.print_exception(
                        f"Length of input lists must be {self.required_length}"
                    )
                    return

        try:
            result = list(zip(*inputs))
        except ValueError:
            self.print_exception("Input lists must have the same length")
            return
        self.out_port.push(result)


class EmaNode(Node):
    """
    Exponential moving average.
    For each new input, the EMA is updated as follows:

    EMA[0] = input[0]

    EMA[t] = alpha * input[t] + (1 - alpha) * EMA[t-1]

    Every `output_interval` steps, the EMA is outputted.
    """

    category = "data/dynamics"

    def build_node(self):
        super().build_node()
        self.label_topic.set("EMA")
        self.reset_port = self.add_in_port("reset")
        self.in_port = self.add_in_port("input")
        self.out_port = self.add_out_port("output")
        self.alpha = self.add_attribute("alpha", FloatTopic, 0.1, editor_type="float")
        self.output_interval = self.add_attribute(
            "output_interval", IntTopic, 1, editor_type="int"
        )

    def init_node(self):
        super().init_node()
        self.ema = None
        self.count = 0

    def edge_activated(self, edge: Edge, port: InputPort):
        if port == self.reset_port:
            self.ema = None
            return
        if port == self.in_port:
            self.run(self.task, data=edge.get())

    def task(self, data):
        # prevent memory leak
        if is_torch_tensor(data):
            data = data.detach()
        if self.ema is None:
            self.ema = data
        else:
            self.ema = self.alpha.get() * data + (1 - self.alpha.get()) * self.ema
        self.count += 1
        if self.count % self.output_interval.get() == 0:
            self.out_port.push(self.ema)


class MeanNode(Node):
    """
    Calculate the mean of a stream of inputs.
    The mean is calculated as follows:

    mean = (input[0] + input[1] + ... + input[t]) / (t + 1)

    Every `output_interval` steps, the mean is outputted.
    """

    category = "data/dynamics"

    def build_node(self):
        super().build_node()
        self.reset_port = self.add_in_port("reset")
        self.in_port = self.add_in_port("input")
        self.out_port = self.add_out_port("output")
        self.output_interval = self.add_attribute(
            "output_interval", IntTopic, 1, editor_type="int"
        )
        self.reset_when_output = self.add_attribute(
            "reset_when_output",
            GenericTopic[bool],
            False,
            editor_type="toggle",
        )

    def init_node(self):
        super().init_node()
        self.sum = 0
        self.num = 0

    def edge_activated(self, edge: Edge, port: InputPort):
        if port == self.reset_port:
            self.sum = 0
            self.num = 0
            return
        if port == self.in_port:
            self.run(self.task, data=edge.get())

    def task(self, data):
        # prevent memory leak
        if is_torch_tensor(data):
            data = data.detach()
        self.sum += data
        self.num += 1
        if self.num % self.output_interval.get() == 0:
            self.out_port.push(self.sum / self.num)
            if self.reset_when_output.get() == "Yes":
                self.sum = 0
                self.num = 0


class GetAttributeNode(Node):
    """
    Get an attribute of an object.

    :inputs:
        - object: the object
        - attribute_name: the attribute name

    :outputs:
        - attribute: the attribute of the object that has the given name
    """

    category = "data"

    @func()
    def attribute(self, obj: object, attribute_name: str) -> object:
        return getattr(obj, attribute_name)
