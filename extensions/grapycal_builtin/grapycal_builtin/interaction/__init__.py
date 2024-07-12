from grapycal import singletonNode, Node, main_store, StringTopic, ListTopic
import numpy as np
import io
from PIL import Image

from .printNode import *
from .execNode import *
from .image import *

try:
    import torch

    HAS_TORCH = True
    from torch import Tensor
except ImportError:
    HAS_TORCH = False
    Tensor = None


class LabelNode(Node):
    category = "interaction"

    def build_node(self):
        self.shape_topic.set("simple")
        self.css_classes.append("fit-content")
        self.expose_attribute(self.label_topic, editor_type="text")
        self.restore_attributes("label")


@singletonNode(auto_instantiate=False)
class WebcamNode(Node):
    category = "interaction"

    def build_node(self):
        self.label_topic.set("Webcam")
        self.shape_topic.set("simple")
        self.format = self.add_attribute(
            "format",
            StringTopic,
            "numpy",
            editor_type="options",
            options=["torch", "numpy"],
        )
        self.out_port = self.add_out_port("img")
        self.button = self.add_button_control("Start streamimg", "button")

    def init_node(self):
        if self.is_preview.get():
            return
        self.webcam = main_store.webcam
        if not self.is_preview.get():
            self.webcam.image.on_set.add_manual(self._on_image_set)
        self.webcam.source_client.on_set.add_manual(self._source_client_changed)
        self.button.on_click.add_manual(self._btn)

    def _btn(self):
        if self.webcam.source_client.get() == self._server.get_action_source():
            self.webcam.source_client.set(-1)
        else:
            self.webcam.source_client.set(self._server.get_action_source())

    def _source_client_changed(self, source_client: int):
        if source_client == -1:
            self.button.label.set("Start streamimg")
        else:
            self.button.label.set("Streaming from: " + str(source_client))

    def _on_image_set(self, _):
        if len(self.out_port.edges) == 0:
            return
        self.run(self._on_image_set_task)

    def _on_image_set_task(self):
        image_bytes: bytes = main_store.webcam.image.to_binary()
        img = Image.open(io.BytesIO(image_bytes))
        # comvert image to torch or numpy
        if self.format.get() == "torch":
            if not HAS_TORCH:
                self.print_exception(
                    "Torch is not installed. Please select numpy format instead."
                )
            img = torch.from_numpy(np.array(img))
            img = img.permute(2, 0, 1).to(torch.float32) / 255
            if img.shape[0] == 4:
                img = img[:3]
        elif self.format.get() == "numpy":
            img = np.array(img).astype(np.float32).transpose(2, 0, 1) / 255
            if img.shape[0] == 4:
                img = img[:3]

        self.out_port.push(img)

    def destroy(self):
        if not self.is_preview.get():
            self.webcam.image.on_set.remove(self._on_image_set)
            self.webcam.source_client.on_set.remove(self._source_client_changed)
        return super().destroy()


class TemplateNode(Node):
    """
    Used as a placeholder for nodes that are not yet implemented
    """

    def build_node(self):
        self.expose_attribute(self.label_topic, "text")
        self.expose_attribute(
            self.shape_topic, "options", options=["normal", "simple", "round"]
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
