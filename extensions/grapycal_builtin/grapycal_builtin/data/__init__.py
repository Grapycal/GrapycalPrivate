import re

from grapycal import ListTopic, StringTopic
from grapycal.sobjects.controls import TextControl
from grapycal.sobjects.controls.buttonControl import ButtonControl
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.node import Node, deprecated
from grapycal.sobjects.port import InputPort
from grapycal.sobjects.sourceNode import SourceNode
from topicsync.topic import FloatTopic, IntTopic


class VariableNode(SourceNode):
    """

    VariableNode stores a variable in the workspace. It can be used to store data for later use.

    :inputs:
        - run: send in a signal to actively output the variable's value
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
        self.label.set("Variable")
        self.shape.set("simple")
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


@deprecated("Use SplitList or SplitDict instead", "0.12.0", "0.13.0")
class SplitNode(Node):
    """
    SplitNode is used to get items from a list or a dictionary using keys.
    It is equivalent to `data[key]` in Python.

    Multiple keys can be used at the same time. Each value will be sent to a corresponding output port.

    :inputs:
        - list/dict: the list or dictionary to be split

    :outputs:
        - value1: the value of the first key
        - value2: the value of the second key
        etc.
    """

    category = "data"

    def build_node(self):
        self.in_port = self.add_in_port("list/dict", 1)
        self.label.set("Split")
        self.shape.set("normal")
        self.keys = self.add_attribute("keys", ListTopic, editor_type="list")
        self.key_mode = self.add_attribute(
            "key mode",
            StringTopic,
            "string",
            editor_type="options",
            options=["string", "eval"],
        )

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
            if self.key_mode.get() == "eval":
                out_port.push(eval(f"_data[{key}]", self.get_vars(), {"_data": data}))
            else:
                out_port.push(data[key])


class SplitListNode(Node):
    """ """

    category = "data"

    def build_node(self):
        self.in_port = self.add_in_port("list", 1)
        self.label.set("Split List")
        self.shape.set("normal")
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


class SplitDictNode(Node):
    """ """

    category = "data"

    def build_node(self):
        self.in_port = self.add_in_port("dict", 1)
        self.label.set("Split Dict")
        self.shape.set("normal")
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

    def build_node(self):
        self.out_port = self.add_out_port("output")
        self.label.set("Build String")
        self.shape.set("normal")
        self.keys = self.add_attribute("keys", ListTopic, editor_type="list")
        self.add_button = self.add_control(ButtonControl, name="add", label="Add")

        if not self.is_new:
            for key in self.keys:
                self.add_item(key, -1)
        else:
            self.keys.insert("1")
            self.add_item("1", -1)

    def init_node(self):
        self.keys.on_insert.add_auto(self.add_item)
        self.keys.on_pop.add_auto(self.remove_item)
        self.add_button.on_click.add_auto(self.add_pressed)

    def add_item(self, key, position):
        self.add_in_port(
            key,
            1,
            display_name="",
            control_type=TextControl,
            activation_mode=TextControl.ActivationMode.NO_ACTIVATION,
        )

    def remove_item(self, key, position):
        self.remove_in_port(key)

    def add_pressed(self):
        new_key = 0
        for key in self.keys:
            if re.match(r"[0-9]+", key):
                new_key = max(new_key, int(key))
        new_key += 1
        self.keys.insert(str(new_key))

    def double_click(self):
        self.task()

    def edge_activated(self, edge: Edge, port: InputPort):
        self.task()

    def task(self):
        if not all([port.is_all_ready() for port in self.in_ports]):
            return
        result = ""
        for key in self.keys:
            result += self.get_in_port(key).get()
        self.out_port.push(result)
        self.flash_running_indicator()


class BuildDictNode(Node):
    category = "data"

    def build_node(self):
        self.out_port = self.add_out_port("output")
        self.label.set("Build Dict")
        self.shape.set("normal")
        self.keys = self.add_attribute("keys", ListTopic, editor_type="list")

        if not self.is_new:
            for key in self.keys:
                self.add_item(key, -1)

    def init_node(self):
        self.keys.on_insert.add_auto(self.add_item)
        self.keys.on_pop.add_auto(self.remove_item)

    def add_item(self, key, position):
        self.add_in_port(
            key,
            1,
            control_type=TextControl,
            activation_mode=TextControl.ActivationMode.NO_ACTIVATION,
        )

    def remove_item(self, key, position):
        self.remove_in_port(key)

    def double_click(self):
        self.task()

    def edge_activated(self, edge: Edge, port: InputPort):
        self.task()

    def task(self):
        if not all([port.is_all_ready() for port in self.in_ports]):
            return
        result = {}
        for key in self.keys:
            result[key] = self.get_in_port(key).get()
        self.out_port.push(result)
        self.flash_running_indicator()


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
        self.in_port = self.add_in_port(
            "string",
            1,
            control_type=TextControl,
            activation_mode=TextControl.ActivationMode.NO_ACTIVATION,
        )
        self.pattern_port = self.add_in_port(
            "pattern",
            1,
            control_type=TextControl,
            activation_mode=TextControl.ActivationMode.NO_ACTIVATION,
        )
        self.out_port = self.add_out_port("matches")
        self.label.set("Regex Find All")
        self.shape.set("normal")
        self.css_classes.append("fit-content")

    def edge_activated(self, edge: Edge, port: InputPort):
        self.task()

    def double_click(self):
        self.task()

    def task(self):
        for port in [self.in_port, self.pattern_port]:
            if not port.is_all_ready():
                return
        string = self.in_port.get()
        pattern = self.pattern_port.get()
        self.out_port.push(re.findall(pattern, string))
        self.flash_running_indicator()


class ZipNode(Node):
    """
    ZipNode is used to combine multiple lists into a single list.

    :inputs:
        - list1: the first list
        - list2: the second list
        etc.

    :outputs:
        - list: the combined list
    """

    category = "data"

    def build_node(self):
        self.out_port = self.add_out_port("output")
        self.label.set("Zip")
        self.shape.set("normal")
        self.items = self.add_attribute("items", ListTopic, editor_type="list")
        self.add_button = self.add_control(ButtonControl, name="add", label="Add")
        self.required_length = self.add_control(
            TextControl, name="required_length", label="Required Length"
        )

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

    def double_click(self):
        self.task()

    def edge_activated(self, edge: Edge, port: InputPort):
        self.task()

    def task(self):
        if not all([port.is_all_ready() for port in self.in_ports]):
            return
        inputs = []
        required_length_str = self.required_length.text.get()
        try:
            required_length = int(required_length_str)
        except ValueError:
            required_length = None
        for item in self.items:
            inputs.append(self.get_in_port(item).get())

        if required_length is not None:
            for input_list in inputs:
                if len(input_list) != required_length:
                    self.print_exception(
                        f"Length of input lists must be {required_length}"
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
    Exponential moving average
    """

    category = "data/dynamics"

    def build_node(self):
        super().build_node()
        self.label.set("EMA")
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
        if self.ema is None:
            self.ema = data
        else:
            self.ema = self.alpha.get() * data + (1 - self.alpha.get()) * self.ema
        self.count += 1
        if self.count % self.output_interval.get() == 0:
            self.out_port.push(self.ema)


class MeanNode(Node):
    """
    Average
    """

    category = "data/dynamics"

    def build_node(self):
        super().build_node()
        self.label.set("Average")
        self.reset_port = self.add_in_port("reset")
        self.in_port = self.add_in_port("input")
        self.out_port = self.add_out_port("output")
        self.output_interval = self.add_attribute(
            "output_interval", IntTopic, 1, editor_type="int"
        )
        self.reset_when_output = self.add_attribute(
            "reset_when_output",
            StringTopic,
            "No",
            editor_type="options",
            options=["Yes", "No"],
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
        self.sum += data
        self.num += 1
        if self.num % self.output_interval.get() == 0:
            self.out_port.push(self.sum / self.num)
            if self.reset_when_output.get() == "Yes":
                self.sum = 0
                self.num = 0
