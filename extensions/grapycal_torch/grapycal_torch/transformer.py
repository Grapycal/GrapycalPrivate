from grapycal import FunctionNode, Node, func
from grapycal_torch.moduleNode import SimpleModuleNode
from torch import nn
import torch


class MultiHeadAttentionNode(SimpleModuleNode):
    module_type = nn.MultiheadAttention
    default_override = {"batch_first": True}

    def get_label(self, params):
        return f"MultiHeadAttn {params['embed_dim']}"


class TransformerEncoderLayerNode(SimpleModuleNode):
    module_type = nn.TransformerEncoderLayer
    default_override = {"batch_first": True}

    def get_label(self, params):
        return f"TransformerEncoderLayer\n dim={params['d_model']}, head={params['nhead']}, dim_ff={params['dim_feedforward']}"


class TransformerDecoderLayerNode(SimpleModuleNode):
    module_type = nn.TransformerDecoderLayer
    default_override = {"batch_first": True}

    def get_label(self, params):
        return f"TransformerDecoderLayer\n dim={params['d_model']}, head={params['nhead']}, dim_ff={params['dim_feedforward']}"


class BinaryPositionalEncodingNode(FunctionNode):
    """
    looks like this:
    00001111
    00110011
    01010101
    """

    inputs = ["length", "dim", "batch_size"]
    max_in_degree = [1, 1, 1]
    outputs = ["output"]

    def calculate(self, length: int, dim: int, batch_size: int) -> torch.Tensor:
        res = []
        for i in range(length):
            res.append([int(x) for x in f"{i:0{dim}b}"])
        return (
            torch.tensor(res, dtype=torch.float32).unsqueeze(0).repeat(batch_size, 1, 1)
        )


class LinearPositionalEncodingNode(FunctionNode):
    """
    looks like this:
    0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9
    """

    inputs = ["length", "batch_size"]
    max_in_degree = [1, 1]
    outputs = ["output"]

    def calculate(self, length: int, batch_size: int) -> torch.Tensor:
        res = []
        for i in range(length):
            res.append([i / length])
        return (
            torch.tensor(res, dtype=torch.float32).unsqueeze(0).repeat(batch_size, 1, 1)
        )


class SinusoidalPositionalEncodingNode(Node):
    """
    looks like this:
    sin(0) cos(0) sin(1) cos(1) sin(2) cos(2) ...
    """

    @func()
    def output(self, length: int, dim: int, batch_size: int) -> torch.Tensor:
        res = []
        for d in range(dim // 2):
            res.append(torch.sin(torch.arange(length) / 10000 ** (2 * d / dim)))
        for d in range(dim // 2):
            res.append(torch.cos(torch.arange(length) / 10000 ** (2 * d / dim)))
        return torch.stack(res, dim=1).unsqueeze(0).repeat(batch_size, 1, 1)


class GenerateSquareSubsequenceMaskNode(Node):
    category = "torch/generative"
    label = "Square Subseq Mask"

    @func()
    def mask(self, length: int = 1) -> torch.Tensor:
        return torch.nn.Transformer.generate_square_subsequent_mask(length)
