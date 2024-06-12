from grapycal.extension_api.trait import Parameter
from torch import nn

from .moduleNode import SimpleModuleNode


class LinearNode(SimpleModuleNode):
    module_type = nn.Linear
    hyper_parameters = [
        Parameter("in_features", "int", 1),
        Parameter("out_features", "int", 1),
    ]

    def get_label(self, params):
        return f"Linear {params['in_features']} → {params['out_features']}"


class CustomModuleNode(SimpleModuleNode):
    category = "torch/neural network"

    def build_node(self):
        super().build_node()
        self.label.set("Custom Module")
        self.module_text = self.add_text_control("", "", name="module_text")
        self.css_classes.append("fit-content")

    def create_module(self) -> nn.Module:
        return eval(self.module_text.get(), self.get_vars())


class FlattenNode(SimpleModuleNode):
    module_type = nn.Flatten
