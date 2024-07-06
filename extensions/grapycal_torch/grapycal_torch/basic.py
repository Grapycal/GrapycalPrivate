from torch import nn

from .moduleNode import SimpleModuleNode


class LinearNode(SimpleModuleNode):
    module_type = nn.Linear

    def get_label(self, params):
        return f"Linear {params['in_features']} → {params['out_features']}"


class CustomModuleNode(SimpleModuleNode):
    category = "torch/neural network"

    def build_node(self):
        super().build_node()
        self.label_topic.set("Custom Module")
        self.module_text = self.add_text_control("", "", name="module_text")
        self.css_classes.append("fit-content")

    def create_module(self) -> nn.Module:
        return eval(self.module_text.get(), self.get_vars())


class FlattenNode(SimpleModuleNode):
    module_type = nn.Flatten
