
from grapycal import Node
from grapycal.sobjects.node import singletonNode
from objectsync import StringTopic

from grapycal_torch.store import GrapycalTorchStore


@singletonNode()
class SettingsNode(Node):
    def build_node(self):
        # TODO: discorver devices on the machine
        self.default_device = self.add_attribute("default device", StringTopic, "cpu", editor_type="options", options=["cpu", "cuda"],target='global',display_name='Torch/default device')
        self.get_store(GrapycalTorchStore).settings = self