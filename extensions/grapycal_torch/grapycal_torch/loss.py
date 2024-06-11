from torch import nn

from .moduleNode import SimpleModuleNode


class BCEWithLogitsLossNode(SimpleModuleNode):
    module_type = nn.BCEWithLogitsLoss


class CrossEntropyLossNode(SimpleModuleNode):
    module_type = nn.CrossEntropyLoss


class MSELossNode(SimpleModuleNode):
    module_type = nn.MSELoss


class L1LossNode(SimpleModuleNode):
    module_type = nn.L1Loss
