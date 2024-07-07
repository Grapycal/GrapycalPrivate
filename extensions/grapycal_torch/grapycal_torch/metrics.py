from typing import Any

from grapycal.sobjects.functionNode import FunctionNode


class AccuracyNode(FunctionNode):
    category = "torch/metrics"
    inputs = ["prediction", "target"]
    outputs = ["accuracy"]
    max_in_degree = [1, 1]

    def build_node(self):
        super().build_node()
        self.label_topic.set("Accuracy")
        self.shape_topic.set("simple")
        self.icon_path_topic.set("metrics")

    def calculate(self, prediction, target) -> Any:
        # TODO: if target is one-hot encoded, convert it to class labels
        prediction = prediction.argmax(dim=-1)
        acc = (prediction == target).float().mean()
        return acc
