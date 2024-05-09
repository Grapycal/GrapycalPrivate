import enum
import io
import json
from typing import Any, Dict, List

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


import requests


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


class TemplateNode(Node):
    def build_node(self):
        self.expose_attribute(self.label, "text")
        self.expose_attribute(
            self.shape, "options", options=["normal", "simple", "round"]
        )
        self.restore_attributes("shape", "label")
        self.in_ports_topic = self.add_attribute(
            "in_ports_topic", ListTopic, [], editor_type="list", display_name="in_ports"
        )
        self.out_ports_topic = self.add_attribute(
            "out_ports_topic",
            ListTopic,
            [],
            editor_type="list",
            display_name="out_ports",
        )

        for port_name in self.in_ports_topic.get():
            self.add_in_port(port_name)
        for port_name in self.out_ports_topic.get():
            self.add_out_port(port_name)

    def init_node(self):
        self.in_ports_topic.on_insert.add_auto(self.on_inport_insert)
        self.in_ports_topic.on_pop.add_auto(self.on_inport_pop)
        self.out_ports_topic.on_insert.add_auto(self.on_outport_insert)
        self.out_ports_topic.on_pop.add_auto(self.on_outport_pop)

    def on_inport_insert(self, port_name, _):
        self.add_in_port(port_name)

    def on_inport_pop(self, port_name, _):
        self.remove_in_port(port_name)

    def on_outport_insert(self, port_name, _):
        self.add_out_port(port_name)

    def on_outport_pop(self, port_name, _):
        self.remove_out_port(port_name)
