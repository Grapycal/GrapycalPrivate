from grapycal.extension_api.trait import Parameter
from .moduleNode import SimpleModuleNode
from torch import nn


class Conv2dNode(SimpleModuleNode):
    module_type = nn.Conv2d
    icon_path = "cnn"
    hyper_parameters = [
        Parameter("in_channels", "int", 1),
        Parameter("out_channels", "int", 1),
        Parameter("kernel_size", "str", "3"),
        Parameter("padding", "str", "1"),
        Parameter("stride", "str", "1"),
        Parameter("dilation", "str", "1"),
    ]

    def get_label(self, params):
        return f"Conv2d {params['in_channels']} → {params['out_channels']} {params['kernel_size']}"


class ConvTranspose2dNode(SimpleModuleNode):
    module_type = nn.ConvTranspose2d
    icon_path = "cnn"
    hyper_parameters = [
        Parameter("in_channels", "int", 1),
        Parameter("out_channels", "int", 1),
        Parameter("kernel_size", "str", "3"),
        Parameter("padding", "str", "1"),
        Parameter("stride", "str", "1"),
        Parameter("dilation", "str", "1"),
    ]

    def get_label(self, params):
        return f"ConvTr2d {params['in_channels']} → {params['out_channels']} {params['kernel_size']}"
