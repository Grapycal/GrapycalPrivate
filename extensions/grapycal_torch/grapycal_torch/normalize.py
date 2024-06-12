from grapycal.extension_api.trait import Parameter
from torch import nn

from .moduleNode import SimpleModuleNode


class BatchNorm2dNode(SimpleModuleNode):
    module_type = nn.BatchNorm2d
    hyper_parameters = [
        Parameter("num_features", "int", 1),
        Parameter("eps", "float", 1e-05),
        Parameter("momentum", "float", 0.1),
        Parameter("affine", "bool", True),
        Parameter("track_running_stats", "bool", True),
    ]

    def get_label(self, params):
        return f"BatchNorm2d {params['num_features']}"


class Dropout2dNode(SimpleModuleNode):
    module_type = nn.Dropout2d
    hyper_parameters = [
        Parameter("p", "float", 0.5),
    ]


class DropoutNode(SimpleModuleNode):
    module_type = nn.Dropout
    hyper_parameters = [
        Parameter("p", "float", 0.5),
    ]
