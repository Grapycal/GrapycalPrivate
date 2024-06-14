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


class SinusoidalPositionalEncodingNode(FunctionNode):
    """
    looks like this:
    sin(0) cos(0) sin(1) cos(1) sin(2) cos(2) ...
    """

    inputs = ["length", "dim", "batch_size"]
    max_in_degree = [1, 1, 1]
    outputs = ["output"]

    def calculate(self, length: int, dim: int, batch_size: int) -> torch.Tensor:
        res = []
        for d in range(dim // 2):
            res.append(torch.sin(torch.arange(length) / 10000 ** (2 * d / dim)))
        for d in range(dim // 2):
            res.append(torch.cos(torch.arange(length) / 10000 ** (2 * d / dim)))
        return torch.stack(res, dim=1).unsqueeze(0).repeat(batch_size, 1, 1)


class RotaryPositionalEmbedding(nn.Module):
    def __init__(self, d_model, max_seq_len):
        super(RotaryPositionalEmbedding, self).__init__()

        # # Create a rotation matrix.
        # self.rotation_matrix = torch.zeros(d_model, d_model, device=torch.device("cuda"))
        # for i in range(d_model):
        #     for j in range(d_model):
        #         self.rotation_matrix[i, j] = torch.cos(i * j * 0.01)

        # # Create a positional embedding matrix.
        # self.positional_embedding = torch.zeros(max_seq_len, d_model, device=torch.device("cuda"))
        # for i in range(max_seq_len):
        #     for j in range(d_model):
        #         self.positional_embedding[i, j] = torch.cos(i * j * 0.01)

        # Create a rotation matrix.
        i, j = torch.meshgrid(torch.arange(d_model), torch.arange(d_model))
        self.rotation_matrix = torch.cos(i * j * 0.01)
        self.register_buffer("rotation_matrix", self.rotation_matrix)

        # Create a positional embedding matrix.
        i, j = torch.meshgrid(torch.arange(max_seq_len), torch.arange(d_model))
        self.positional_embedding = torch.cos(i * j * 0.01)
        self.register_buffer("positional_embedding", self.positional_embedding)

    def forward(self, x):
        """
        Args:
            x: A tensor of shape (batch_size, seq_len, d_model).

        Returns:
            A tensor of shape (batch_size, seq_len, d_model).
        """

        # Add the positional embedding to the input tensor.
        x += self.positional_embedding

        # Apply the rotation matrix to the input tensor.
        x = torch.matmul(x, self.rotation_matrix)

        return x


class RotaryPositionalEmbeddingNode(SimpleModuleNode):
    module_type = RotaryPositionalEmbedding
    hyper_parameters = [
        Parameter("d_model", "int", 1),
        Parameter("max_seq_len", "int", 1),
    ]

    def get_label(self, params):
        return f"RoPE dim={params['d_model']}, max_len={params['max_seq_len']}"
