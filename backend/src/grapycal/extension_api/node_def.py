from ast import FunctionType
from collections import defaultdict
from dataclasses import dataclass
from types import MethodType
from typing import TYPE_CHECKING
from .trait import Trait

if TYPE_CHECKING:
    from grapycal.sobjects.node import Node


@dataclass
class NodeDefInfo:
    funcs: dict[str, MethodType]
    params: dict[str, MethodType]


def get_node_def_info(node_type):
    funcs = {}
    params = {}
    for name in dir(node_type):
        attr = getattr(node_type, name)
        if hasattr(attr, "_is_node_func"):
            funcs[name] = attr
        if hasattr(attr, "_is_node_param"):
            params[name] = attr
    return NodeDefInfo(funcs, params)


class DecorTrait(Trait):
    def __init__(self, funcs: dict[str, MethodType], params: dict[str, MethodType]):
        super().__init__('_decor')
        self.funcs = funcs
        self.params = params
        inputs = []
        outputs = []
        for func in funcs.values():
            func = m
            for 

def generate_traits(node: "Node", node_def_info: NodeDefInfo) -> "list[Trait]":
    traits: "list[Trait]" = []

    inputs = defaultdict(list)
    outputs = defaultdict(list)

    for func in node_def_info.funcs.values():
        if 'return' in func.__annotations__:
            outputs[func.__name__] = func.__annotations__['return']
        for name, annotation in func.__annotations__.items():
            inputs[name].append(annotation)

    for param in node_def_info.params.values():
        

    traits.append(DecorTrait(node_def_info.funcs, node_def_info.params))

    return traits
