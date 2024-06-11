from torch import nn

from .moduleNode import SimpleModuleNode


class BCEWithLogitsLossNode(SimpleModuleNode):
    category = "torch/loss"
    inputs = ["prediction", "target"]
    max_in_degree = [None]
    outputs = ["loss"]

    def build_node(self):
        super().build_node()
        self.label.set("BCEWithLogitsLoss")
        self.icon_path.set("metrics")

    def create_module(self) -> nn.Module:
        return nn.BCEWithLogitsLoss()

    def generate_label(self):
        return "BCEWithLogitsLoss"

    def forward(self, prediction, target):
        return self.module(prediction, target)


class CrossEntropyLossNode(SimpleModuleNode):
    category = "torch/loss"
    inputs = ["prediction", "target"]
    max_in_degree = [None]
    outputs = ["loss"]

    def build_node(self):
        super().build_node()
        self.label.set("CrossEntropyLoss")
        self.icon_path.set("metrics")

    def create_module(self) -> nn.Module:
        return nn.CrossEntropyLoss()

    def generate_label(self):
        return "CrossEntropyLoss"

    def forward(self, prediction, target):
        return self.module(prediction, target)


class MSELossNode(SimpleModuleNode):
    category = "torch/loss"
    inputs = ["prediction", "target"]
    max_in_degree = [None]
    outputs = ["loss"]

    def build_node(self):
        super().build_node()
        self.label.set("MSELoss")
        self.icon_path.set("metrics")

    def create_module(self) -> nn.Module:
        return nn.MSELoss()

    def generate_label(self):
        return "MSELoss"

    def forward(self, prediction, target):
        return self.module(prediction, target)


class L1LossNode(SimpleModuleNode):
    category = "torch/loss"
    inputs = ["prediction", "target"]
    max_in_degree = [None]
    outputs = ["loss"]

    def build_node(self):
        super().build_node()
        self.label.set("L1Loss")
        self.icon_path.set("metrics")

    def create_module(self) -> nn.Module:
        return nn.L1Loss()

    def generate_label(self):
        return "L1Loss"

    def forward(self, prediction, target):
        return self.module(prediction, target)
