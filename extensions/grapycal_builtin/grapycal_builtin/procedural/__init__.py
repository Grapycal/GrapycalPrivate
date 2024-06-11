import time
from collections import defaultdict
from typing import Any

from grapycal.extension.utils import NodeInfo
from grapycal.sobjects.controlPanel import ControlPanel
from grapycal.sobjects.controls.textControl import TextControl
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.functionNode import FunctionNode
from grapycal.sobjects.port import InputPort
from objectsync.sobject import SObjectSerialized

from grapycal_builtin.utils import ListDict, ListDictWithNotify

from .forNode import *
from .funcDef import *
from .limiterNode import LimiterNode
from .stepsNode import StepsNode
from .clock import ClockNode

from grapycal import Node


class TaskNodeManager:
    trigger_nodes = ListDict["TriggerNode"]()
    task_nodes = ListDictWithNotify["TaskNode"]()
    task_nodes.key_added += ControlPanel.add_task
    task_nodes.key_removed += ControlPanel.remove_task


class TriggerNode(Node):
    category = "procedural"

    def build_node(self):
        self.shape.set("simple")
        self.name = self.add_attribute("name", StringTopic, editor_type="text")
        self.in_port = self.add_in_port("jump", display_name="")
        self.out_port = self.add_out_port("then", display_name="")
        self.css_classes.append("fit-content")
        self.label.set(f"{self.name.get()}")

    def init_node(self):
        if self.is_preview.get():
            return

        TaskNodeManager.trigger_nodes.append(self.name.get(), self)
        self.name.on_set2.add_manual(self.on_name_set)

    def on_name_set(self, old, new):
        if self.is_preview.get():
            return

        self.label.set(f"{new}")
        TaskNodeManager.trigger_nodes.remove(old, self)
        TaskNodeManager.trigger_nodes.append(new, self)

    def edge_activated(self, edge: Edge, port: InputPort):
        data = edge.get()
        self.run(self.after_jump, to_queue=False, data=data)
        for node in TaskNodeManager.task_nodes.get(self.name.get()):
            node.jump(data)

    def double_click(self):
        if self.is_preview.get():
            return

        data = None
        self.run(self.after_jump, to_queue=False, data=data)
        for node in TaskNodeManager.task_nodes.get(self.name.get()):
            node.jump(data)

    def after_jump(self, data):
        self.out_port.push(data)

    def destroy(self) -> SObjectSerialized:
        if self.is_preview.get():
            return super().destroy()

        TaskNodeManager.trigger_nodes.remove(self.name.get(), self)
        return super().destroy()


class TaskNode(Node):
    category = "procedural"

    def build_node(self):
        self.shape.set("simple")
        self.name = self.add_attribute("name", StringTopic, editor_type="text")
        self.out_port = self.add_out_port("do", display_name="")
        self.css_classes.append("fit-content")

    def init_node(self):
        if self.is_preview.get():
            return

        TaskNodeManager.task_nodes.append(self.name.get(), self)
        self.label.set(f"{self.name.get()}")
        self.name.on_set2.add_manual(self.on_name_set)
        ControlPanel.on_run_task += self.on_run_task

    def on_name_set(self, old, new):
        if self.is_preview.get():
            return

        self.label.set(f"{new}")
        TaskNodeManager.task_nodes.remove(old, self)
        TaskNodeManager.task_nodes.append(new, self)

    def double_click(self):
        if self.is_preview.get():
            return

        for node in TaskNodeManager.task_nodes.get(self.name.get()):
            node.jump(None)

    def jump(self, data):
        self.run(self.out_port.push, data=data)

    def on_run_task(self, task):
        if task == self.name.get():
            self.jump(None)

    def destroy(self) -> SObjectSerialized:
        if self.is_preview.get():
            return super().destroy()

        TaskNodeManager.task_nodes.remove(self.name.get(), self)
        ControlPanel.on_run_task -= self.on_run_task
        return super().destroy()


class SleepNode(FunctionNode):
    category = "procedural"
    inputs = ["start"]
    outputs = ["done"]

    def build_node(self):
        super().build_node()
        time_port = self.add_in_port(
            "seconds", control_type=TextControl, display_name="time", text="1"
        )
        self.shape.set("normal")
        self.label.set("Sleep")
        self.time_control = time_port.default_control

    def calculate(self, **inputs) -> Any:
        time.sleep(float(self.time_control.get()))
        return inputs["start"]


class IfNode(Node):
    category = "procedural"

    def build_node(self):
        self.shape.set("round")
        self.add_in_port("if")
        self.then_port = self.add_out_port("then")
        self.else_port = self.add_out_port("else")

    def port_activated(self, port: InputPort):
        self.flash_running_indicator()
        cond = port.get()
        if cond:
            self.then_port.push(None)
        else:
            self.else_port.push(None)
