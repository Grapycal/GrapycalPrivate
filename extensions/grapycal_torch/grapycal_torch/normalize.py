from torch import nn

from .moduleNode import SimpleModuleNode


class BatchNorm2dNode(SimpleModuleNode):
    module_type = nn.BatchNorm2d

    def get_label(self, params):
        return f"BatchNorm2d {params['num_features']}"


class Dropout2dNode(SimpleModuleNode):
    module_type = nn.Dropout2d


class DropoutNode(SimpleModuleNode):
    module_type = nn.Dropout
