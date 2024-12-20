from grapycal import ListTopic, Node, ObjDictTopic, TextControl, Edge, InputPort
from .math import *


class LambdaNode(Node):
    """
    Define one or more outputs based on one or more inputs using expressions. Similar to a lambda function in Python.

    For each output, the node
    provides an input box for you to define the function with an expression.

    :inputs:
        - *inputs: You can add any number of inputs to the node.

    :outputs:
        - *outputs: You can add any number of outputs to the node.

    """

    category = "function"

    def build_node(self):
        self.label_topic.set("Lambda")
        self.shape_topic.set("normal")
        self.text_controls = self.add_attribute(
            "text_controls", ObjDictTopic[TextControl], restore_from=None
        )

        self.input_args = self.add_attribute(
            "input_args", ListTopic, editor_type="list"
        )
        self.outputs = self.add_attribute("outputs", ListTopic, editor_type="list")
        self.css_classes.append("fit-content")

        if self.is_new:
            self.input_args.insert("x")
            self.on_input_arg_added("x", 0)
            self.outputs.insert("")
            self.on_output_added("", 0)
            self.text_controls[""].text.set("x")
        else:
            for arg in self.input_args:
                self.on_input_arg_added(arg, -1)
            for out in self.outputs:
                self.on_output_added(out, -1)

    def init_node(self):
        self.input_args.add_validator(ListTopic.unique_validator)
        self.input_args.on_insert.add_auto(self.on_input_arg_added)
        self.input_args.on_pop.add_auto(self.on_input_arg_removed)

        self.outputs.add_validator(ListTopic.unique_validator)
        self.outputs.on_insert.add_auto(self.on_output_added)
        self.outputs.on_pop.add_auto(self.on_output_removed)

    def on_input_arg_added(
        self, arg_name, position
    ):  # currently only support adding to the end
        self.add_in_port(arg_name, 1, display_name=arg_name)

    def on_input_arg_removed(self, arg_name, position):
        self.remove_in_port(arg_name)

    def on_output_added(self, name, position):
        self.add_out_port(name, display_name=name)
        new_control = self.add_control(TextControl, name=name)
        self.text_controls[name] = new_control
        new_control.label.set(f"{name} = ")

    def on_output_removed(self, name, position):
        self.remove_out_port(name)
        self.text_controls.pop(name)
        self.remove_control(name)

    def input_edge_added(self, edge: Edge, port: InputPort):
        self.calculate()

    def edge_activated(self, edge: Edge, port: InputPort):
        self.calculate()

    def calculate(self):
        for port in self.in_ports:
            if not port.is_all_ready():
                return
            if len(port.edges) == 0:
                return
        arg_values = [port.get() for port in self.in_ports]

        def task():
            for out_name, text_control in self.text_controls.get().items():
                expr = f'lambda {",".join(self.input_args)}: {text_control.text.get()}'
                y = eval(expr, self.get_vars())(*arg_values)
                self.get_out_port(out_name).push(y)

        self.run(task)
