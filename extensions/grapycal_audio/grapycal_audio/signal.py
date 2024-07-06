from grapycal import Node
from grapycal.sobjects.controls.textControl import TextControl
from grapycal.sobjects.port import InputPort


class AddNode(Node):
    category = "audio/signal"

    def build_node(self):
        self.in_port1 = self.add_in_port("input 1", 1)
        self.in_port2 = self.add_in_port("input 2", 1)
        self.out_port = self.add_out_port("output")
        self.label_topic.set("Add")

    def port_activated(self, port: InputPort):
        if self.in_port1.is_all_ready() and self.in_port2.is_all_ready():
            self.run(self.task, background=False)

    def task(self):
        data1 = self.in_port1.get()
        data2 = self.in_port2.get()
        self.out_port.push(data1 + data2)


class MultiplyNode(Node):
    category = "audio/signal"

    def build_node(self):
        self.in_port1 = self.add_in_port("input 1", 1)
        self.in_port2 = self.add_in_port("input 2", 1)
        self.out_port = self.add_out_port("output")
        self.label_topic.set("Multiply")

    def port_activated(self, port: InputPort):
        if self.in_port1.is_all_ready() and self.in_port2.is_all_ready():
            self.run(self.task, background=False)

    def task(self):
        data1 = self.in_port1.get()
        data2 = self.in_port2.get()
        self.out_port.push(data1 * data2)


class GainNode(Node):
    category = "audio/signal"

    def build_node(self):
        self.in_port1 = self.add_in_port("input", 1)
        self.in_port2 = self.add_in_port("gain", 1, control_type=TextControl, text="1")
        self.out_port = self.add_out_port("output")
        self.label_topic.set("Gain")

    def port_activated(self, port: InputPort):
        if self.in_port1.is_all_ready() and self.in_port2.is_all_ready():
            self.run(self.task, background=False)

    def task(self):
        data = self.in_port1.get()
        gain = float(self.in_port2.get())
        self.out_port.push(data * gain)
