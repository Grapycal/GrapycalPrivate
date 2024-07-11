import time
from typing import Any

from grapycal.extension_api.decor import func
from grapycal.sobjects.controlPanel import ControlPanel
from grapycal.sobjects.controls.textControl import TextControl
from grapycal.sobjects.controls.triggerControl import TriggerControl
from grapycal import InputPort, param
from objectsync.sobject import SObjectSerialized

from grapycal_builtin.utils import ListDict, ListDictWithNotify

from .forNode import *
from .funcDef import *
from .limiterNode import LimiterNode
from .stepsNode import StepsNode
from .clock import ClockNode

from grapycal import Node


class TaskNodeManager:
    runtask_nodes = ListDict["RunTaskNode"]()
    task_nodes = ListDictWithNotify["TaskNode"]()
    task_nodes.key_added += ControlPanel.add_task
    task_nodes.key_removed += ControlPanel.remove_task


class RunTaskNode(Node):
    category = "procedural"

    def build_node(self):
        self.shape_topic.set("simple")
        self.name = self.add_attribute("name", StringTopic, editor_type="text")
        self.in_port = self.add_in_port(
            "jump",
            display_name="",
            control_type=TriggerControl,
            activate_on_control_change=True,
        )
        self.out_port = self.add_out_port("then", display_name="")
        self.css_classes.append("fit-content")
        self.label_topic.set(f"{self.name.get()}")

    def init_node(self):
        if self.is_preview.get():
            return

        TaskNodeManager.runtask_nodes.append(self.name.get(), self)
        self.name.on_set2.add_manual(self.on_name_set)

    def on_name_set(self, old, new):
        if self.is_preview.get():
            return

        self.label_topic.set(f"{new}")
        TaskNodeManager.runtask_nodes.remove(old, self)
        TaskNodeManager.runtask_nodes.append(new, self)

    def port_activated(self, port: InputPort):
        if self.is_preview.get():
            return
        data = port.get()
        self.flash_running_indicator()
        self.run(self.after_jump, to_queue=False, data=data)
        for node in TaskNodeManager.task_nodes.get(self.name.get()):
            node.jump(data)

    def after_jump(self, data):
        self.out_port.push(data)

    def destroy(self) -> SObjectSerialized:
        if self.is_preview.get():
            return super().destroy()

        TaskNodeManager.runtask_nodes.remove(self.name.get(), self)
        return super().destroy()


class TaskNode(Node):
    category = "procedural"

    def build_node(self):
        self.shape_topic.set("simple")
        self.name = self.add_attribute(
            "name", StringTopic, editor_type="text", init_value="Task"
        )
        self.out_port = self.add_out_port("do", display_name="")
        self.css_classes.append("fit-content")

    def init_node(self):
        if self.is_preview.get():
            return

        TaskNodeManager.task_nodes.append(self.name.get(), self)
        self.label_topic.set(f"{self.name.get()}")
        self.name.on_set2.add_manual(self.on_name_set)
        ControlPanel.on_run_task += self.on_run_task

    def on_name_set(self, old, new):
        if self.is_preview.get():
            return

        self.label_topic.set(f"{new}")
        TaskNodeManager.task_nodes.remove(old, self)
        TaskNodeManager.task_nodes.append(new, self)

    def icon_clicked(self):
        if self.is_preview.get():
            return

        if self.name.get() == "":
            self.jump(None)
        else:
            for node in TaskNodeManager.task_nodes.get(self.name.get()):
                node.jump(None)

    def jump(self, data):
        self.run(self.out_port.push, data=data)

    def on_run_task(self, task):
        if self.name.get() == "":
            return
        if task == self.name.get():
            self.jump(None)

    def destroy(self) -> SObjectSerialized:
        if self.is_preview.get():
            return super().destroy()

        TaskNodeManager.task_nodes.remove(self.name.get(), self)
        ControlPanel.on_run_task -= self.on_run_task
        return super().destroy()


class SleepNode(Node):
    category = "procedural"

    @param()
    def param(self, seconds: float = 1):
        self.seconds = seconds

    @func()
    def done(self):
        time.sleep(self.seconds)


class IfNode(Node):
    category = "procedural"

    def build_node(self):
        self.shape_topic.set("round")
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
