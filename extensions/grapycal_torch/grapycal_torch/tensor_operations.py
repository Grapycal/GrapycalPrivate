from typing import Any

import einops
from grapycal.sobjects.port import InputPort
import torch
import torch.nn.functional as F
from grapycal import FunctionNode, IntTopic, Node
from grapycal.extension.utils import NodeInfo
from grapycal.sobjects.controls.sliderControl import SliderControl
from grapycal.sobjects.controls.textControl import TextControl
from topicsync.topic import StringTopic


class CatNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inputs"]
    outputs = ["out"]

    def build_node(self):
        super().build_node()
        self.shape_topic.set("round")
        self.dim = self.add_attribute("dim", IntTopic, 0, editor_type="int")
        self.dim_changed(self.dim.get())

    def init_node(self):
        super().init_node()
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self, dim):
        self.label_topic.set("C" + str(dim))

    def calculate(self, inputs: list[Any]):
        return torch.cat(inputs, dim=self.dim.get())


class StackNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inputs"]
    outputs = ["out"]

    def build_node(self):
        super().build_node()
        self.dim = self.add_attribute("dim", IntTopic, editor_type="int")
        self.label_topic.set("☰0")
        self.shape_topic.set("round")
        self.dim_changed(self.dim.get())

    def init_node(self):
        super().init_node()
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self, dim):
        self.label_topic.set("☰" + str(dim))

    def calculate(self, inputs: list[Any]):
        return torch.stack(inputs, dim=self.dim.get())


class UnsqueezeNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inputs"]
    outputs = ["out"]
    display_port_names = False

    def build_node(self):
        super().build_node()
        self.dim = self.add_attribute("dim", IntTopic, editor_type="int")
        self.label_topic.set("U0")
        self.shape_topic.set("round")
        self.dim_changed(self.dim.get())

    def init_node(self):
        super().init_node()
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self, dim):
        self.label_topic.set("U" + str(dim))

    def calculate(self, inputs):
        return torch.unsqueeze(inputs[0], dim=self.dim.get())


class SqueezeNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inputs"]
    outputs = ["out"]
    display_port_names = False

    def build_node(self):
        super().build_node()
        self.dim = self.add_attribute("dim", IntTopic, editor_type="int")
        self.label_topic.set("S0")
        self.shape_topic.set("round")
        self.dim_changed(self.dim.get())

    def init_node(self):
        super().init_node()
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self, dim):
        self.label_topic.set("S" + str(dim))

    def calculate(self, inputs):
        return torch.squeeze(inputs[0], dim=self.dim.get())


class RearrangeNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inputs"]
    outputs = ["out"]

    def build_node(self):
        super().build_node()
        self.pattern_control = self.add_control(
            TextControl, name="pattern_control", label=""
        )
        self.label_topic.set("Rearrange")
        self.shape_topic.set("simple")
        self.css_classes.append("fit-content")

    def init_node(self):
        super().init_node()
        if self.is_new:
            self.pattern_control.text.set("b c h w -> b (c h w)")

    def calculate(self, inputs):
        raw_arg = self.pattern_control.text.get().split(",")
        pattern = raw_arg[0]
        axes_lengths = {}
        for arg in raw_arg[1:]:
            key, value = arg.split("=")
            key = key.strip()
            value = int(value.strip())
            axes_lengths[key] = value

        return einops.rearrange(inputs[0], pattern, **axes_lengths)


class BackwardNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inputs"]

    def build_node(self):
        super().build_node()
        self.label_topic.set("↤")
        self.shape_topic.set("round")

    def calculate(self, inputs: list[Any]):
        inputs[0].backward()


class ToCudaNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inputs"]
    outputs = ["tensor"]
    display_port_names = False

    def build_node(self):
        super().build_node()
        self.label_topic.set("cu")
        self.shape_topic.set("round")

    def calculate(self, inputs: list[Any]):
        return inputs[0].cuda()


class FConv2DNode(FunctionNode):
    category = "torch/operations"
    inputs = ["x", "kernel"]
    max_in_degree = [1, 1]
    outputs = ["result"]

    def build_node(self):
        super().build_node()
        self.label_topic.set("Conv2D")
        self.shape_topic.set("normal")
        self.icon_path_topic.set("cnn")

    def calculate(self, x: torch.Tensor, kernel: torch.Tensor):
        is_c1hw = False
        orig_x = x
        if len(x.shape) == 2:
            x = x.unsqueeze(0)
        if len(kernel.shape) == 2:
            kernel = kernel.unsqueeze(0).unsqueeze(0)
        elif len(kernel.shape) == 3:
            kernel = kernel.unsqueeze(0)
        if len(x.shape) == 3 and x.shape[0] != 1 and kernel.shape[1] == 1:
            is_c1hw = True
            x = x.unsqueeze(1)
        y = F.conv2d(x, kernel, padding=kernel.shape[-1] // 2)
        if is_c1hw:
            y = y.squeeze(1)
        if len(orig_x.shape) == 2:
            y = y.squeeze(0)
        return y


class SinNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inp"]
    outputs = ["result"]
    max_in_degree = [1]
    display_port_names = False

    def build_node(self):
        super().build_node()
        self.label_topic.set("sin")
        self.shape_topic.set("round")

    def calculate(self, inp):
        return torch.sin(inp)


class CosNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inp"]
    outputs = ["result"]
    max_in_degree = [1]
    display_port_names = False

    def build_node(self):
        super().build_node()
        self.label_topic.set("cos")
        self.shape_topic.set("round")

    def calculate(self, inp):
        return torch.cos(inp)


class CumprodNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inp"]
    outputs = ["result"]
    max_in_degree = [1]
    display_port_names = False

    def build_node(self):
        super().build_node()
        self.label_topic.set("cumprod 0")
        self.shape_topic.set("simple")
        self.dim = self.add_attribute("dim", IntTopic, 0, editor_type="int")

    def init_node(self):
        super().init_node()
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self, dim):
        self.label_topic.set("cumprod " + str(dim))

    def restore_from_version(self, version: str, old: NodeInfo):
        super().restore_from_version(version, old)
        self.restore_attributes("dim")

    def calculate(self, inp):
        return torch.cumprod(inp, dim=self.dim.get())


class GatherNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inp", "index"]
    outputs = ["result"]
    max_in_degree = [1, 1]

    def build_node(self):
        super().build_node()
        self.label_topic.set("gather 0")
        self.shape_topic.set("simple")
        self.dim = self.add_attribute("dim", IntTopic, 0, editor_type="int")

    def init_node(self):
        super().init_node()
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self, dim):
        self.label_topic.set("gather " + str(dim))

    def restore_from_version(self, version: str, old: NodeInfo):
        super().restore_from_version(version, old)
        self.restore_attributes("dim")

    def calculate(self, inp, index):
        return torch.gather(inp, dim=self.dim.get(), index=index)


def choose_from_top(probs, n=20):
    ind = torch.topk(probs, n).indices
    top_prob = probs[ind]
    top_prob = top_prob / (top_prob).sum()  # Normalize
    choice = torch.multinomial(top_prob, 1)[0]
    token_id = ind[choice]
    return int(token_id)


class ChooseFromTopNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inp"]
    outputs = ["result"]
    max_in_degree = [1, 1]

    def build_node(self):
        super().build_node()
        self.label_topic.set("ChooseFromTop")
        self.shape_topic.set("normal")
        self.mode = self.add_attribute(
            "mode",
            StringTopic,
            "probs",
            editor_type="options",
            options=["probs", "logits"],
        )
        self.n = self.add_in_port(
            "n", 1, control_type=SliderControl, value=20, min=1, max=40, int_mode=True
        )

    def init_node(self):
        super().init_node()
        self.mode.on_set.add_manual(self.mode_changed)
        self.mode_changed(self.mode.get())

    def mode_changed(self, mode):
        self.get_in_port("inp").display_name.set(mode)

    def calculate(self, inp):
        if self.mode.get() == "logits":
            probs = torch.softmax(inp, dim=0)
        else:
            probs = inp

        n = self.n.get()

        if len(probs.shape) == 2:
            result = []
            for i in range(probs.shape[0]):
                result.append(choose_from_top(probs[i], n))
            return torch.tensor(result)
        else:
            return choose_from_top(probs, n)


class SoftmaxNode(FunctionNode):
    category = "torch/operations"
    inputs = ["inp"]
    outputs = ["result"]
    max_in_degree = [1]

    def build_node(self):
        super().build_node()
        self.label_topic.set("Softmax")
        self.shape_topic.set("normal")

    def calculate(self, inp):
        return torch.softmax(inp, dim=0)


class GetGradientNode(Node):
    """
    Get the gradient of the input tensor. If the input tensor does not have a gradient, the node registers a hook to get the gradient when it is available and outputs it.
    """

    category = "torch/operations"
    label = "∇"

    def build_node(self):
        self.shape_topic.set("round")
        self.add_in_port("tensor", 1)
        self.grad_port = self.add_out_port("grad")

    def port_activated(self, port: InputPort):
        tensor: torch.Tensor = port.get()
        if tensor.retains_grad is False or tensor.grad is None:
            tensor.register_hook(self.hook)
        else:
            self.grad_port.push(tensor.grad)

    def hook(self, grad):
        self.grad_port.push(grad)
