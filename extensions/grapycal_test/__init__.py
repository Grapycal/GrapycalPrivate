import enum
import io
import json
from typing import Any, Dict, List

from grapycal.core.typing import PlainType
from grapycal.extension_api.decor import func, param
from grapycal.sobjects.controls.sliderControl import SliderControl
import websockets
from grapycal import (
    ButtonControl,
    DictTopic,
    Edge,
    FunctionNode,
    InputPort,
    IntTopic,
    ListTopic,
    Node,
    SetTopic,
    StringTopic,
    TextControl,
    ToggleControl,
)
from grapycal.core.workspace import Workspace
from grapycal.extension.utils import NodeInfo
from grapycal.sobjects.controls.imageControl import ImageControl
from grapycal.sobjects.DVfunctionNode import DVfunctionNode
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import InputPort
from objectsync.sobject import SObjectSerialized
from websockets.sync.client import connect


class OUONode(Node):
    category = "test"

    def build_node(self):
        self.label.set("testing")
        self.add_control(ToggleControl, name="toggle_conutrol", label="toggle")

        self.add_control(ToggleControl, name="toggle_conetrol", label="toeuytggle")

        self.add_control(ToggleControl, name="toggle_control", label="togeytuetyugle")


class TestNode(FunctionNode):
    category = "test"
    default_ports = []

    def build_node(self):
        self.label.set("testing")
        self.send_port = self.add_in_port("send")
        self.recv_port = self.add_out_port("recv")
        self.subs_info = self.add_attribute(
            "subs_info",
            DictTopic,
            {},
            editor_type="dict",
            key_options=["aaa0", "aab"],
            value_options=["vads,asde"],
            key_strict=True,
        )  # internal use only. data: {'name':str,'type':str}
        # self.subsciptions = self.add_attribute('subsciptions', ListTopic, [], editor_type='list') # for user to manipulate

    def init_node(self):
        # def link_subsciptions_to_subs_info():
        #     self.subsciptions.on_insert.add_auto(lambda topic_name,_: self.subs_info.add(topic_name, self.subscription_type.get()))
        #     self.subsciptions.on_pop.add_auto(lambda topic_name,_: self.subs_info.pop(topic_name))
        # self._server.do_after_transition(link_subsciptions_to_subs_info)

        self.subs_info.on_add.add_auto(self.on_subscription_add1)
        self.subs_info.on_remove.add_auto(self.on_subscription_remove1)

    def on_subscription_add1(self, topic_name, topic_value):
        # self.ports_value.update({topic_name:topic_value})
        self.default_ports.append(topic_name)
        self.add_in_port(topic_name)

    def on_subscription_remove1(self, topic_name):
        # self.ports_value.pop(topic_name)
        self.default_ports.remove(topic_name)
        self.remove_in_port(topic_name)

    def restore_from_version(self, version: str, old: NodeInfo):
        super().restore_from_version(version, old)
        self.restore_attributes("subs_info")

    def calculate(self, **kwargs):
        for key, value in self.subs_info.get().items():
            if self.get_in_port(key).edges:
                continue
            kwargs.update({key: eval(value)})

        print(self.default_ports)
        print(self.subs_info.get())
        print("calculate")
        return kwargs


class DefaultTestNode(DVfunctionNode):
    category = "test"
    default_value = [{"a": 1, "b": 2, "c": 3}]
    default_only = False

    def build_node(self):
        super().build_node()
        self.label.set("default testing")
        self.shape.set("normal")
        self.send_port = self.add_in_port("test")
        self.recv_port = self.add_out_port("b")
        self.inputs_attribute.add("ccccc", "<requests.get>")
        self._default_value.append("ccccc")
        self.add_in_port("ccccc")

    def calculate(self, **kwargs):
        return kwargs


class Test1Node(Node):
    category = "test"

    def build_node(self):
        self.add_in_port("int", datatype=PlainType(int))
        self.add_in_port("string", datatype=PlainType(str))
        self.add_out_port("int", datatype=PlainType(int))
        self.add_out_port("string", datatype=PlainType(str))

        self.int_topic = self.add_attribute("some_int_topic", IntTopic)
        self.string_topic = self.add_attribute("some_string_topic", StringTopic)


class OldAddNode(Node):
    def build_node(self):
        self.a = self.add_in_port(
            "a", datatype=PlainType(int), control_type=SliderControl
        )
        self.b = self.add_in_port(
            "b", datatype=PlainType(int), control_type=SliderControl
        )
        self.result = self.add_out_port("result", datatype=PlainType(int))

    def port_activated(self, port: InputPort):
        if port == self.a or port == self.b:
            if self.a.is_all_ready() and self.b.is_all_ready():
                self.result.push(self.a.get() + self.b.get())


class NewAddNode(Node):
    def init_node(self):
        self.bias = 0

    @func()
    def sum(self, a: int, b: int, c: int) -> int:
        return a + b + c + self.bias


class BiasNode(NewAddNode):
    @param()
    def param(self, bias: int) -> None:
        self.bias = bias
        self.label.set(f"bias: {bias}")
