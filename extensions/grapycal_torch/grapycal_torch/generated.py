import torch
from grapycal.utils.nodeGen import F2NSpecFull as Spec
from grapycal.utils.nodeGen import functions2nodes

funcs = [
    torch.cuda.memory_allocated,
]

for attr_name in [
    "temperature",
    "memory_allocated",
]:
    if hasattr(torch.cuda, attr_name):
        funcs.append(getattr(torch.cuda, attr_name))

generated_nodes = functions2nodes(
    *funcs,
    default_spec=Spec(
        prefix="Cuda",
    ),
)
