import torch
from grapycal.utils.nodeGen import F2NSpecFull as Spec
from grapycal.utils.nodeGen import functions2nodes

generated_nodes = functions2nodes(
    torch.cuda.temperature,
    torch.cuda.memory_allocated,
    torch.cuda.power_draw,
    default_spec=Spec(
        prefix="Cuda",
    ),
)
