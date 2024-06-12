from grapycal.extension_api.trait import (
    Parameter,
)
from grapycal.sobjects.functionNode import FunctionNode
from grapycal_torch.moduleNode import SimpleModuleNode
from torch import nn
import torch


class MultiHeadAttentionNode(SimpleModuleNode):
    module_type = nn.MultiheadAttention
    hyper_parameters = [
        Parameter("embed_dim", "int", 1),
        Parameter("num_heads", "int", 1),
        Parameter("dropout", "float", 0.0),
        Parameter("bias", "bool", True),
        Parameter("add_bias_kv", "bool", False),
        Parameter("add_zero_attn", "bool", False),
        Parameter("kdim", "int", 1),
        Parameter("vdim", "int", 1),
    ]

    def get_label(self, params):
        return f"MultiHeadAttn {params['embed_dim']}"


class TransformerEncoderLayerNode(SimpleModuleNode):
    module_type = nn.TransformerEncoderLayer
    hyper_parameters = [
        Parameter("d_model", "int", 1),
        Parameter("nhead", "int", 1),
        Parameter("dim_feedforward", "int", 1),
        Parameter("dropout", "float", 0.1),
        Parameter("activation", "str", "relu"),
        Parameter("batch_first", "bool", True),
    ]
    inputs = ["src"]  # will allow more after we have optional inputs feature

    def get_label(self, params):
        return f"TransformerEncoderLayer\n dim={params['d_model']}, head={params['nhead']}, dim_ff={params['dim_feedforward']}"


class TransformerDecoderLayerNode(SimpleModuleNode):
    module_type = nn.TransformerDecoderLayer
    hyper_parameters = [
        Parameter("d_model", "int", 1),
        Parameter("nhead", "int", 1),
        Parameter("dim_feedforward", "int", 1),
        Parameter("dropout", "float", 0.1),
        Parameter("activation", "str", "relu"),
        Parameter("batch_first", "bool", True),
    ]
    inputs = ["memory", "tgt"]  # will allow more after we have optional inputs feature

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
