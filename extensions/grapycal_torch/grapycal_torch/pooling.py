from grapycal.extension_api.trait import Parameter
from grapycal_torch.moduleNode import SimpleModuleNode
from torch import nn


class MaxPool2dNode(SimpleModuleNode):
    module_type = nn.MaxPool2d
    icon_path = "cnn"
    hyper_parameters = [
        Parameter("kernel_size", "int", 2),
        Parameter("stride", "int", 2),
        Parameter("padding", "int", 0),
        Parameter("dilation", "int", 1),
    ]

    def get_label(self, params):
        return f"MaxPool2d {params['kernel_size']} {params['stride']}"
