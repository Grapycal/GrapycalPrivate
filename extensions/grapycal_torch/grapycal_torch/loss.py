from torch import nn

from .moduleNode import SimpleModuleNode


class LossBaseNode(SimpleModuleNode):
    def get_label(self, params):
        return self.module_type.__name__


class BCEWithLogitsLossNode(LossBaseNode):
    module_type = nn.BCEWithLogitsLoss


class CrossEntropyLossNode(LossBaseNode):
    module_type = nn.CrossEntropyLoss


class MSELossNode(LossBaseNode):
    module_type = nn.MSELoss
    annotation_override = {"size_average": bool, "reduce": bool}
    default_override = {"size_average": True, "reduce": True}


class L1LossNode(LossBaseNode):
    module_type = nn.L1Loss
