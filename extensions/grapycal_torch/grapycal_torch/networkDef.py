from collections import defaultdict
from typing import TYPE_CHECKING, List

from grapycal import GRID, ListTopic, Node, StringTopic
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import InputPort, OutputPort
from grapycal.stores import main_store
from objectsync.sobject import SObjectSerialized
from torch import Tensor

from grapycal_torch.store import GrapycalTorchStore

from .utils import find_next_valid_name

if TYPE_CHECKING:
    from . import GrapycalTorch


class NetworkCallNode(Node):
    """
    A NetworkCallNode represents a call to a network, specified by name.
    Once you set the network name to the NetworkCallNode, Grapycal will search for a NetworkInNode and a NetworkOutNode existing
    in the workspace with the same name. Then, its ports will be updated accroding to the network
    definition.
    """

    ext: "GrapycalTorch"
    category = "torch/neural network"

    def build_node(self, name: str = "Network"):
        self.label_topic.set("")
        self.shape_topic.set("normal")
        self.icon_path_topic.set("nn")
        self.network_name = self.add_attribute(
            "network name", StringTopic, editor_type="text", init_value=name
        )
        self.network_name.add_validator(
            lambda x, _: x != ""
        )  # empty name may confuse users
        self.mode_control = self.add_option_control(
            name="mode", options=["train", "eval"], value="train", label="Mode"
        )
        # manually restore in_ports and out_ports
        if not self.is_new:
            assert self.old_node_info is not None
            for port in self.old_node_info.in_ports.values():
                self.add_in_port(port.name, 1, display_name=port.name)
            for port in self.old_node_info.out_ports.values():
                self.add_out_port(port.name, display_name=port.name)

        self.update_ports()

    def init_node(self):
        self.network_name.on_set2.add_manual(self.on_network_name_changed)
        self.network_name.on_set.add_auto(self.on_network_name_changed_auto)
        self.ext.net.calls.append(self.network_name.get(), self)
        self.label_topic.set(f" {self.network_name.get()}")

    def on_network_name_changed(self, old, new):
        self.label_topic.set(f"{new}")
        self.ext.net.calls.remove(old, self)
        self.ext.net.calls.append(new, self)

    def on_network_name_changed_auto(self, new):
        self.update_ports()

    def update_ports(self):
        self.update_input_ports()
        self.update_output_ports()

    def update_input_ports(self):
        if self.network_name.get() not in self.ext.net.ins:
            return
        names = self.ext.net.ins[self.network_name.get()].outs.get()

        edgesd = defaultdict[str, list[OutputPort]](list)

        # reversed is a hack to make port order consistent when undoing (although it's not very important)
        for port in reversed(self.in_ports.get().copy()):
            name = port.get_name()
            for edge in port.edges.copy():
                edgesd[name].append(edge.get_tail())
                edge.remove()
            self.remove_in_port(name)

        for name in names:
            port = self.add_in_port(name, 1)
            edges = edgesd.get(name, [])
            for tail in edges:
                self.editor.create_edge(tail, port)

    def update_output_ports(self):
        if self.network_name.get() not in self.ext.net.outs:
            return
        names = self.ext.net.outs[self.network_name.get()].ins.get()

        edgesd = defaultdict[str, list[InputPort]](list)

        for port in self.out_ports.get().copy():
            name = port.get_name()
            for edge in port.edges.copy():
                edgesd[name].append(edge.get_head())
                edge.remove()
            self.remove_out_port(name)

        for name in names:
            port = self.add_out_port(name)
            edges = edgesd.get(name, [])
            for head in edges:
                self.editor.create_edge(port, head)

    def edge_activated(self, edge: Edge, port):
        for port in self.in_ports:
            if not port.is_all_ready():
                return

        if self.network_name.get() not in self.ext.net.ins:
            return

        self.run(self.end_function, to_queue=False)
        self.run(self.start_function, to_queue=False)

    def start_function(self):
        if self.is_destroyed():
            return

        self.ext.net.set_mode(self.network_name.get(), self.mode_control.get())

        inputs = {}
        for port in self.in_ports:
            inputs[port.name.get()] = port.get()

        self.ext.net.ins[self.network_name.get()].start_function(inputs)

    def end_function(self):
        if self.is_destroyed():
            return
        if self.network_name.get() not in self.ext.net.outs:
            return  # assume its intended to be a void function
        self.ext.net.outs[self.network_name.get()].end_function(self)

    def push_result(self, result: dict):
        for key, value in result.items():
            self.get_out_port(key).push(value)

    def destroy(self) -> SObjectSerialized:
        self.ext.net.calls.remove(self.network_name.get(), self)
        return super().destroy()


class NetworkInNode(Node):
    ext: "GrapycalTorch"
    category = "torch/neural network"

    def build_node(self, name: str = "Network", inputs: List[str] | None = None):
        if inputs is None:
            inputs = ["x"]

        self.shape_topic.set("normal")
        self.icon_path_topic.set("nn")

        # setup attributes
        # The self.outs attribute is actually "inputs" of the network, but it was mistakenly named "outs" and I didn't want to change it to avoid breaking backwards compatibility
        self.outs = self.add_attribute(
            "outs",
            ListTopic,
            editor_type="list",
            init_value=inputs,
            display_name="inputs",
        )
        self.outs.add_validator(ListTopic.unique_validator)
        self.device_control = self.add_option_control(
            name="device",
            options=["default", "cpu", "cuda"],
            value="default",
            label="Device",
        )
        self.create_reference_btn = self.add_button_control(
            name="create_reference", label="Create reference"
        )

        self.network_name = self.add_attribute(
            "network name", StringTopic, editor_type="text", init_value=name
        )
        self.network_name.add_validator(
            lambda x, _: x not in self.ext.net.ins
        )  # function name must be unique
        self.network_name.add_validator(
            lambda x, _: x != ""
        )  # empty name may confuse users
        try:
            self.restore_attributes("network name")
        except Exception:
            self.network_name.set(name)

        self.network_name.set(
            find_next_valid_name(self.network_name.get(), self.ext.net.ins)
        )

        self.file_path = self.add_attribute(
            "file path", StringTopic, editor_type="text", init_value=f"{name}.pt"
        )
        self.save_btn = self.add_button_control(name="save", label="Save")
        self.load_btn = self.add_button_control(name="load", label="Load")

        self.update_label()

        for out in self.outs.get():
            self.add_out_port(out, display_name=out)

    def init_node(self):
        self.torch_store = self.get_store(GrapycalTorchStore)

        if not self.is_preview.get():
            self.ext.net.add_in(self.network_name.get(), self)
        self.create_reference_btn.on_click.add_auto(self._create_reference)

        self.save_btn.on_click.add_manual(lambda: self.run(self.save))
        self.load_btn.on_click.add_manual(lambda: self.run(self.load))

        # add callbacks to attributes
        self.outs.on_insert.add_auto(self.on_output_added)
        self.outs.on_pop.add_auto(self.on_output_removed)
        self.outs.on_set.add_auto(self.on_output_set)

        self.network_name.on_set2.add_manual(self.on_network_name_changed)
        self.network_name.on_set.add_auto(self.on_network_name_changed_auto)

    def save(self):
        self.ext.net.save_network(self.network_name.get(), self.file_path.get())
        self.flash_running_indicator()
        main_store.send_message_to_all(
            f"Saved {self.network_name.get()} to {self.file_path.get()}."
        )

    def load(self):
        self.ext.net.load_network(self.network_name.get(), self.file_path.get(), self)
        self.flash_running_indicator()
        main_store.send_message_to_all(
            f"Loaded {self.network_name.get()} from {self.file_path.get()}."
        )

    def post_create(self):
        for call in self.ext.net.calls.get(self.network_name.get()):
            call.update_ports()

    def on_network_name_changed(self, old, new):
        if not self.is_preview.get():
            self.ext.net.remove_in(old)
            self.ext.net.add_in(new, self)
        self.update_label()

    def on_network_name_changed_auto(self, new):
        if not self.is_preview.get():
            for call in self.ext.net.calls.get(self.network_name.get()):
                call.update_ports()

    def update_label(self):
        self.label_topic.set(f"{self.network_name.get()}")

    def on_output_added(self, name, position):
        self.add_out_port(name, display_name=name)

    def on_output_removed(self, name, position):
        self.remove_out_port(name)

    def on_output_set(self, new):
        if not self.is_preview.get():
            for call in self.ext.net.calls.get(self.network_name.get()):
                call.update_input_ports()

    def start_function(self, args: dict):
        self.ext.net.set_device(self.network_name.get(), self.device_control.get())
        # make sure all input tensors are on the same device
        # TODO: make this optional
        for key, value in args.items():
            if isinstance(value, Tensor):
                value = value.to(self.torch_store.get_device(self.device_control.get()))
            self.get_out_port(key).push(value)
        self.flash_running_indicator()

    def _create_reference(self):
        self.ext.create_node(
            NetworkCallNode,
            name=self.network_name.get(),
            translation=self.get_position([GRID, GRID * 6]),
        )

    def destroy(self) -> SObjectSerialized:
        if not self.is_preview.get():
            self.ext.net.remove_in(self.network_name.get())
        return super().destroy()


class NetworkOutNode(Node):
    ext: "GrapycalTorch"
    category = "torch/neural network"

    def build_node(self, name: str = "Network", outputs: List[str] | None = None):
        if outputs is None:
            outputs = ["y"]
        self.shape_topic.set("normal")
        self.icon_path_topic.set("nn")

        # setup attributes
        self.ins = self.add_attribute(
            "ins",
            ListTopic,
            editor_type="list",
            init_value=outputs,
            display_name="outputs",
        )
        self.ins.add_validator(ListTopic.unique_validator)
        self.restore_attributes("ins")

        self.network_name = self.add_attribute(
            "network name", StringTopic, editor_type="text", init_value=name
        )
        self.network_name.add_validator(
            lambda x, _: x not in self.ext.net.outs
        )  # function name must be unique
        self.network_name.add_validator(
            lambda x, _: x != ""
        )  # empty name may confuse users
        try:
            self.restore_attributes("network name")
        except Exception:
            self.network_name.set(name)

        self.network_name.set(
            find_next_valid_name(self.network_name.get(), self.ext.net.outs)
        )

        for in_ in self.ins.get():
            self.add_in_port(in_, 1, display_name=in_)

    def init_node(self):
        # add callbacks to attributes
        self.ins.on_insert.add_auto(self.on_input_added)
        self.ins.on_pop.add_auto(self.on_input_removed)
        self.ins.on_set.add_auto(self.on_input_set)

        self.network_name.on_set2.add_manual(self.on_network_name_changed)
        self.network_name.on_set.add_auto(self.on_network_name_changed_auto)

        self.update_label()

        if not self.is_preview.get():
            self.ext.net.add_out(self.network_name.get(), self)

    def post_create(self):
        for call in self.ext.net.calls.get(self.network_name.get()):
            call.update_ports()

    def on_network_name_changed(self, old, new):
        if not self.is_preview.get():
            self.ext.net.remove_out(old)
            self.ext.net.add_out(new, self)
        self.update_label()

    def on_network_name_changed_auto(self, new):
        if not self.is_preview.get():
            for call in self.ext.net.calls.get(self.network_name.get()):
                call.update_ports()

    def update_label(self):
        self.label_topic.set(f"{self.network_name.get()}")

    def on_input_added(self, name, position):
        self.add_in_port(name, 1, display_name=name)

    def on_input_removed(self, name, position):
        self.remove_in_port(name)

    def on_input_set(self, new):
        if not self.is_preview.get():
            for call in self.ext.net.calls.get(self.network_name.get()):
                call.update_output_ports()

    def end_function(self, caller: NetworkCallNode):
        for port in self.in_ports:
            if not port.is_all_ready():
                self.print_exception(
                    RuntimeError(f"Output data missing for {port.name.get()}")
                )
                return
        result = {key: self.get_in_port(key).get() for key in self.ins.get()}
        caller.push_result(result)
        self.flash_running_indicator()

    def destroy(self) -> SObjectSerialized:
        if not self.is_preview.get():
            self.ext.net.remove_out(self.network_name.get())
        return super().destroy()
