from grapycal.extension_api.trait import Parameter
from .moduleNode import SimpleModuleNode
from torch import nn


class Conv2dNode(SimpleModuleNode):
    module_type = nn.Conv2d
    default_override = {"in_channels": 1, "out_channels": 1, "kernel_size": 3}
    icon_path = "cnn"


class ConvTranspose2dNode(SimpleModuleNode):
    module_type = nn.ConvTranspose2d
    icon_path = "cnn"
    hyper_parameters = [
        Parameter("in_channels", "int", 1),
        Parameter("out_channels", "int", 1),
        Parameter("kernel_size", "int", 3),
        Parameter("padding", "int", 1),
        Parameter("stride", "int", 1),
        Parameter("dilation", "int", 1),
    ]
    inputs = ["input"]

    def get_label(self, params):
        return f"ConvTr2d {params['in_channels']} → {params['out_channels']} {params['kernel_size']}"
