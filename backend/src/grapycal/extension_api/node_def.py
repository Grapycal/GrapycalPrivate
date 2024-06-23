"""
A high-level API for defining nodes in Grapycal.
"""

from collections import defaultdict
from dataclasses import dataclass
import inspect
import logging
from types import MethodType
from typing import TYPE_CHECKING, Any

from grapycal.core.typing import AnyType, GType
from grapycal.sobjects.controls.floatControl import FloatControl
from grapycal.sobjects.controls.intControl import IntControl
from grapycal.sobjects.controls.nullControl import NullControl
from grapycal.sobjects.controls.textControl import TextControl
from grapycal.sobjects.controls.toggleControl import ToggleControl
from grapycal.sobjects.port import OutputPort
from objectsync.topic import ObjDictTopic
from .trait import Trait
from grapycal.sobjects.port import InputPort

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


@dataclass
class NodeDefInfo:
    funcs: dict[str, MethodType]
    params: dict[str, MethodType]


def get_node_def_info(attrs: dict[str, Any]):
    funcs = {}
    params = {}
    for name, obj in attrs.items():
        if hasattr(obj, "_is_node_func"):
            funcs[name] = obj
        if hasattr(obj, "_is_node_param"):
            params[name] = obj
    return NodeDefInfo(funcs, params)


@dataclass
class NodeFunc:
    name: str
    inputs: dict[str, GType]
    outputs: dict[str, GType]
    background: bool = True


@dataclass
class NodeParam:
    name: str
    params: dict[str, GType]


@dataclass
class PortInfo:
    is_func: bool
    used_by_funcs: list[NodeFunc]
    used_by_params: list[NodeParam]


class DecorTrait(Trait):
    def __init__(
        self,
        inputs: dict[str, GType],
        outputs: dict[str, GType],
        params: dict[str, GType],
        node_funcs: dict[str, NodeFunc],
        node_params: dict[str, NodeParam],
    ):
        super().__init__("_decor")
        self.inputs = inputs
        self.outputs = outputs
        self.params = params
        self.node_funcs = node_funcs
        self.node_params = node_params

    def build_node(self):
        self.in_ports = self.node.add_attribute(
            f"{self.name}.in_ports", ObjDictTopic[InputPort], restore_from=None
        )
        self.out_ports = self.node.add_attribute(
            f"{self.name}.out_ports", ObjDictTopic[OutputPort], restore_from=None
        )
        self.param_ports = self.node.add_attribute(
            f"{self.name}.param_ports", ObjDictTopic[InputPort], restore_from=None
        )

        # generate input ports for function inputs
        for name, gtype in self.inputs.items():
            self.in_ports[f"{self.name}.in.{name}"] = self.add_input_or_param_port(
                f"{self.name}.in.{name}", name, gtype, activate_on_control_change=False
            )

        # generate output ports for function outputs
        for name, gtype in self.outputs.items():
            self.out_ports[f"{self.name}.out.{name}"] = self.node.add_out_port(
                f"{self.name}.out.{name}", display_name=name, datatype=gtype
            )

        # generate param ports for function params
        for name, gtype in self.params.items():
            self.param_ports[f"{self.name}.param.{name}"] = (
                self.add_input_or_param_port(
                    f"{self.name}.param.{name}",
                    name,
                    gtype,
                    activate_on_control_change=True,
                )
            )

    def init_node(self):
        self.port_info_dict: defaultdict[str, PortInfo] = defaultdict(
            lambda: PortInfo(False, [], [])
        )
        for node_func in self.node_funcs.values():
            for name in node_func.inputs:
                self.port_info_dict[f"{self.name}.in.{name}"].is_func = True
                self.port_info_dict[f"{self.name}.in.{name}"].used_by_funcs.append(
                    node_func
                )
        for param in self.node_params.values():
            for name in param.params:
                self.port_info_dict[f"{self.name}.param.{name}"].is_func = False
                self.port_info_dict[f"{self.name}.param.{name}"].used_by_params.append(
                    param
                )
            param_callback = getattr(self.node, param.name)
            self.node.run(  # Call the param callback once to initialize the param
                lambda param_callback=param_callback, param=param: param_callback(
                    **{
                        name: self.param_ports[f"{self.name}.param.{name}"].get()
                        for name in param.params
                    }
                ),
                background=True,
            )

    def add_input_or_param_port(
        self,
        name: str,
        display_name: str,
        gtype: GType,
        activate_on_control_change: bool,
    ) -> "InputPort":
        control_kwargs: dict[str, Any] = {}
        editor_args: dict[str, Any] = {}

        if gtype == AnyType:
            control_type = NullControl
            editor_type = None
        elif gtype >> str:
            control_type = TextControl
            editor_type = "text"
        elif gtype >> bool:
            control_type = ToggleControl
            editor_type = "toggle"
        elif gtype >> int:
            control_type = IntControl
            editor_type = "int"
        elif gtype >> float:
            control_type = FloatControl
            control_kwargs = {"int_mode": False}
            editor_type = "float"

        else:
            logger.warning(
                f"Not support gtype {gtype} for port {name} yet. Will not add control."
            )
            control_type = NullControl
            editor_type = None
        # TODO: add more control types

        port = self.node.add_in_port(
            name,
            1,
            display_name=display_name,
            control_type=control_type,
            activate_on_control_change=activate_on_control_change,
            **control_kwargs,
        )
        if editor_type is not None:
            self.node.expose_attribute(
                port.default_control.get_value_topic(),
                editor_type,
                display_name=display_name,
                **editor_args,
            )
        return port

    def port_activated(self, port: InputPort):
        port_info = self.port_info_dict[port.get_name()]
        peeked_ports: set[InputPort] = set()
        for node_func in port_info.used_by_funcs:
            # A func requires all its inputs to be ready before it can be executed
            if all(
                self.in_ports[f"{self.name}.in.{name}"].is_all_ready()
                for name in node_func.inputs
            ):
                func = getattr(self.node, node_func.name)
                inputs = {
                    name: self.in_ports[f"{self.name}.in.{name}"].peek()
                    for name in node_func.inputs
                }
                for name in node_func.inputs:
                    peeked_ports.add(self.in_ports[f"{self.name}.in.{name}"])
                if node_func.background:
                    self.node.run(
                        lambda func=func,
                        inputs=inputs,
                        node_func=node_func: self.func_finished(  # The node_func=node_func trick is to avoid the late binding problem
                            func(**inputs), node_func
                        ),
                        background=True,
                    )
                else:
                    self.node.run(
                        lambda func=func,
                        inputs=inputs,
                        node_func=node_func: self.func_finished(
                            func(**inputs), node_func
                        ),
                        background=False,
                    )

        for peeked_port in peeked_ports:
            peeked_port.get()

        if not port_info.is_func:  # If the port is a param port
            for node_param in port_info.used_by_params:
                # A param callback is called when any of its input ports are activated
                param_callback = getattr(self.node, node_param.name)
                self.node.run(
                    lambda param_callback=param_callback,
                    node_param=node_param: param_callback(
                        **self.collect_params(node_param)
                    ),
                    background=False,  # assume param callbacks are fast so can be run in the ui thread
                )

    def collect_params(self, node_param: NodeParam):
        params = {}
        for name in node_param.params:
            params[name] = self.param_ports[f"{self.name}.param.{name}"].get()
        return params

    def func_finished(self, outputs, node_func: NodeFunc):
        if len(node_func.outputs) == 1:
            name = f"{self.name}.out.{list(node_func.outputs)[0]}"
            self.out_ports[name].push(outputs)
        else:
            for name, output in outputs.items():
                assert name in node_func.outputs
                self.out_ports[f"{self.name}.out.{name}"].push(output)


def consistent_annotations(annotations: "list[type]") -> bool:
    if len(annotations) == 0:
        return True

    first_annotation = annotations[0]
    for annotation in annotations:
        if annotation is None:
            continue
        if annotation != first_annotation:
            return False

    return True


def collect_input_output_params(
    funcs: dict[str, MethodType], param_funcs: "dict[str, MethodType]"
) -> tuple[
    dict[str, list[Any]],
    dict[str, list[Any]],
    dict[str, list[Any]],
    dict[str, NodeFunc],
    dict[str, NodeParam],
]:
    inputs = defaultdict(list)
    outputs = defaultdict(list)
    params = defaultdict(list)
    node_funcs: dict[str, NodeFunc] = {}
    node_params: dict[str, NodeParam] = {}
    for func in funcs.values():
        cur_inputs: dict[str, GType] = {}
        cur_outputs: dict[str, GType] = {}
        if "return" in func.__annotations__:
            outputs[func.__name__].append(func.__annotations__["return"])
            cur_outputs.update(
                {func.__name__: AnyType}
            )  # The actual type will be filled in later
        else:
            outputs[func.__name__].append(None)
            cur_outputs.update({func.__name__: AnyType})

        signature = inspect.signature(func)
        for name, arg in signature.parameters.items():
            if name == "self":
                continue
            inputs[name].append(
                arg.annotation if arg.annotation != inspect.Parameter.empty else None
            )
            cur_inputs.update({name: AnyType})

        node_funcs[func.__name__] = NodeFunc(
            name=func.__name__, inputs=cur_inputs, outputs=cur_outputs
        )

    for param in param_funcs.values():
        signature = inspect.signature(param)
        cur_params: dict[str, GType] = {}
        for name, arg in signature.parameters.items():
            if name == "self":
                continue
            params[name].append(
                arg.annotation if arg.annotation != inspect.Parameter.empty else None
            )
            cur_params.update({name: AnyType})

        node_params[param.__name__] = NodeParam(name=param.__name__, params=cur_params)

    return inputs, outputs, params, node_funcs, node_params


def consistent_input_output_params(
    inputs: "dict[str, list[Any]]",
    outputs: "dict[str, list[Any]]",
    params: "dict[str, list[Any]]",
) -> bool:
    for name, annotations in inputs.items():
        if not consistent_annotations(annotations):
            logger.warning(
                f"Input {name} has inconsistent annotations between multiple functions. Plese leave only one annotation or make them consistent."
            )
            return False

    for name, annotations in outputs.items():
        if not consistent_annotations(annotations):
            logger.warning(
                f"Output {name} has inconsistent annotations between multiple functions. Plese leave only one annotation or make them consistent."
            )
            return False

    for name, annotations in params.items():
        if not consistent_annotations(annotations):
            logger.warning(
                f"Param {name} has inconsistent annotations between multiple functions. Plese leave only one annotation or make them consistent."
            )
            return False

    return True


def annotations_to_gtype(annotations: "list[Any]") -> "GType":
    for annotation in annotations:
        if annotation is not None:
            return GType.from_annotation(annotation)
    return GType.from_annotation(Any)


def generate_traits(node_def_info: NodeDefInfo) -> "list[Trait]":
    traits: "list[Trait]" = []

    inputs_dict_list, outputs_dict_list, params_dict_list, node_funcs, node_params = (
        collect_input_output_params(node_def_info.funcs, node_def_info.params)
    )

    if not consistent_input_output_params(
        inputs_dict_list, outputs_dict_list, params_dict_list
    ):
        return []

    inputs = {
        name: annotations_to_gtype(annotations)
        for name, annotations in inputs_dict_list.items()
    }
    outputs = {
        name: annotations_to_gtype(annotations)
        for name, annotations in outputs_dict_list.items()
    }
    params = {
        name: annotations_to_gtype(annotations)
        for name, annotations in params_dict_list.items()
    }

    # fill in the actual types for node_funcs and node_params
    for node_func in node_funcs.values():
        node_func.inputs = {name: inputs[name] for name in node_func.inputs}
        node_func.outputs = {name: outputs[name] for name in node_func.outputs}

    for node_param in node_params.values():
        node_param.params = {name: params[name] for name in node_param.params}

    traits.append(DecorTrait(inputs, outputs, params, node_funcs, node_params))
    return traits
