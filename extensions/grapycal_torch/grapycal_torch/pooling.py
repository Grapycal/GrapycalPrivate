from grapycal_torch.moduleNode import SimpleModuleNode
from torch import nn


class MaxPool2dNode(SimpleModuleNode):
    module_type = nn.MaxPool2d
    icon_path = "cnn"
    default_override = {
        "kernel_size": 2,
        "stride": 2,
    }

    def get_label(self, params):
        return f"MaxPool2d {params['kernel_size']} {params['stride']}"
