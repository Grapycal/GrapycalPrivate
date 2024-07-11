from torch import nn

from .moduleNode import SimpleModuleNode


class ReLUNode(SimpleModuleNode):
    module_type = nn.ReLU
    icon_path = "relu"


class LeakyReLUNode(SimpleModuleNode):
    module_type = nn.LeakyReLU
    icon_path = "relu"

    def get_label(self, params):
        return f"LeakyReLU {params['negative_slope']}"


class SigmoidNode(SimpleModuleNode):
    module_type = nn.Sigmoid
    icon_path = "sigmoid"
