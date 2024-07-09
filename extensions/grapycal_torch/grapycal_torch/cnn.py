from .moduleNode import SimpleModuleNode
from torch import nn

class Conv2dNode(SimpleModuleNode):
    module_type = nn.Conv2d
    default_override = {"in_channels": 1, "out_channels": 1, "kernel_size": 3}
    icon_path = "cnn"

    def get_label(self, params):
        return f"Conv2d {params['in_channels']} → {params['out_channels']}, ks={params['kernel_size']}"
    
    @func()
    def transform(self, x: Tensor):
        return self.module(x)

    def type_inference_of_transform(self, x: TensorType):
        shape = x.shape
        return f(x.shape, self.kernel_size ...)

class ConvTranspose2dNode(SimpleModuleNode):
    module_type = nn.ConvTranspose2d
    default_override = {"in_channels": 1, "out_channels": 1, "kernel_size": 3}
    icon_path = "cnn"

    def get_label(self, params):
        return f"ConvTr2d {params['in_channels']} → {params['out_channels']}, ks={params['kernel_size']}"
