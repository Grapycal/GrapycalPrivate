"""
A high-level API for defining nodes in Grapycal.
"""

from collections import defaultdict
from dataclasses import dataclass
import inspect
import logging
import traceback
from typing import TYPE_CHECKING, Any, Callable, Iterable, TypeVar

from grapycal.core.typing import AnyType, GType, LiteralType
from grapycal.sobjects.controls.buttonControl import ButtonControl
from grapycal.sobjects.controls.floatControl import FloatControl
from grapycal.sobjects.controls.intControl import IntControl
from grapycal.sobjects.controls.nullControl import NullControl
from grapycal.sobjects.controls.objectControl import ObjectControl
from grapycal.sobjects.controls.optionControl import OptionControl
from grapycal.sobjects.controls.textControl import TextControl
from grapycal.sobjects.controls.toggleControl import ToggleControl
from grapycal.sobjects.controls.triggerControl import TriggerControl
from grapycal.sobjects.port import UNSPECIFY_CONTROL_VALUE, OutputPort
from objectsync.topic import ObjDictTopic, ListTopic
from .trait import Trait
from grapycal.sobjects.port import InputPort

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class SHOW_ALL_PORTS_T:
    pass


SHOW_ALL_PORTS = SHOW_ALL_PORTS_T()


class NodeFuncSpec:
    def __init__(
        self,
        function: Callable,
        sign_source: Callable | list[Callable | inspect.Parameter] | None = None,
        annotation_override: dict[str, Any] | None = None,
        default_override: dict[str, Any] | None = None,
        shown_ports: list[str] | SHOW_ALL_PORTS_T = SHOW_ALL_PORTS,
        background: bool = True,
        create_trigger_port: bool | None = None,
    ):
        self.name = function.__name__
        if sign_source is None:
            self.sign_source = [function]
        elif not isinstance(sign_source, list):
            self.sign_source = [sign_source]
        else:
            self.sign_source = sign_source
        self.annotation_override = annotation_override or {}
        self.default_override = default_override or {}
        self.shown_ports = shown_ports
        self.background = background
        self.create_trigger_port = create_trigger_port

        # if function is async function, background should be False
        if inspect.iscoroutinefunction(function) and background:
            logger.warning(
                f"Node function {function.__name__} is an async function, background should be False. Setting background to False."
            )
            self.background = False


class NodeParamSpec:
    def __init__(
        self,
        function: Callable,
        sign_source: Callable | list[Callable | inspect.Parameter] | None = None,
        annotation_override: dict[str, Any] | None = None,
        default_override: dict[str, Any] | None = None,
        shown_ports: list[str] | SHOW_ALL_PORTS_T = SHOW_ALL_PORTS,
    ):
        self.name = function.__name__
        if sign_source is None:
            self.sign_source = [function]
        elif not isinstance(sign_source, list):
            self.sign_source = [sign_source]
        else:
            self.sign_source = sign_source
        self.annotation_override = annotation_override or {}
        self.default_override = default_override or {}
        self.shown_ports = shown_ports


@dataclass
class NodeDefInfo:
    funcs: dict[str, NodeFuncSpec]
    params: dict[str, NodeParamSpec]


def get_node_def_info(
    attrs: dict[str, Any], base_info: NodeDefInfo | None = None
) -> NodeDefInfo:
    if base_info is None:
        funcs = {}
        params = {}
    else:
        funcs = base_info.funcs.copy()
        params = base_info.params.copy()

    for name, obj in attrs.items():
        if hasattr(obj, "_node_func_spec"):
            funcs[name] = obj._node_func_spec
        if hasattr(obj, "_node_param_spec"):
            params[name] = obj._node_param_spec
    return NodeDefInfo(funcs, params)


NO_DEFAULT = object()


@dataclass
class Input:
    name: str
    datatype: GType
    default: Any = NO_DEFAULT
    show_port_by_default: bool = True


@dataclass
class Output:
    name: str
    datatype: GType


@dataclass
class ParamItem:
    name: str
    datatype: GType
    default: Any = NO_DEFAULT
    show_port_by_default: bool = True


@dataclass
class NodeFunc:
    name: str
    inputs: dict[str, Input]
    outputs: dict[str, Output]
    spec: NodeFuncSpec


@dataclass
class NodeParam:
    name: str
    params: dict[str, ParamItem]


@dataclass
class PortInfo:
    is_func: bool
    used_by_funcs: list[NodeFunc]
    used_by_params: list[NodeParam]


class DecorTrait(Trait):
    def __init__(
        self,
        inputs: dict[str, Input],
        outputs: dict[str, Output],
        params: dict[str, ParamItem],
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
        self.tr_ports = self.node.add_attribute(
            f"{self.name}.tr_ports", ObjDictTopic[InputPort], restore_from=None
        )

        default_inputs_to_show = [
            input.name for input in self.inputs.values() if input.show_port_by_default
        ]

        self.show_inputs = self.node.add_attribute(
            f"{self.name}.show_inputs",
            ListTopic,
            display_name="Apparance/input",
            editor_type="multiselect",
            options=list(self.inputs.keys()),
            init_value=default_inputs_to_show,
        )

        default_params_to_show = [
            param.name for param in self.params.values() if param.show_port_by_default
        ]

        self.show_params = self.node.add_attribute(
            f"{self.name}.show_params",
            ListTopic,
            display_name="Apparance/param",
            editor_type="multiselect",
            options=list(self.params.keys()),
            init_value=default_params_to_show,
        )

        # generate a trigger input port for each function
        for name, node_func in self.node_funcs.items():
            # Only add trigger port if all inputs have default values. For functions with an input without a default value,
            # it's likely to go wrong if user triggers it without setting the input.
            if (node_func.spec.create_trigger_port is True) or (
                (node_func.spec.create_trigger_port is None)
                and all(
                    map(
                        lambda inp: inp.default != NO_DEFAULT, node_func.inputs.values()
                    )
                )
            ):
                self.tr_ports[f"{self.name}.tr.{name}"] = self.node.add_in_port(
                    f"{self.name}.tr.{name}",
                    64,
                    display_name="trigger",
                    datatype=AnyType,
                    control_type=NullControl
                    if self.node.is_preview.get()
                    else TriggerControl,
                    control_value=UNSPECIFY_CONTROL_VALUE,
                    activate_on_control_change=True,
                    update_control_from_edge=False,
                )
                self.show_inputs.insert(f"{self.name}.tr.{name}")

        # generate input ports for function inputs
        for name, inp in self.inputs.items():
            if name in self.node.input_values:
                control_value = self.node.input_values[name]
            else:
                control_value = (
                    inp.default
                    if inp.default != NO_DEFAULT
                    else UNSPECIFY_CONTROL_VALUE
                )
            self.in_ports[f"{self.name}.in.{name}"] = self.add_input_or_param_port(
                f"{self.name}.in.{name}",
                name,
                f"Default input/{name}",
                inp.datatype,
                control_value,
                activate_on_control_change=False,
                update_control_from_edge=False,
                is_param=False,
            )

        # generate output ports for function outputs
        for name, out in self.outputs.items():
            self.out_ports[f"{self.name}.out.{name}"] = self.node.add_out_port(
                f"{self.name}.out.{name}", display_name=name, datatype=out.datatype
            )

        # generate param ports for function params
        for name, par in self.params.items():
            if name in self.node.param_values:
                control_value = self.node.param_values[name]
            else:
                control_value = (
                    par.default
                    if par.default != NO_DEFAULT
                    else UNSPECIFY_CONTROL_VALUE
                )
            self.param_ports[f"{self.name}.param.{name}"] = (
                self.add_input_or_param_port(
                    f"{self.name}.param.{name}",
                    name,
                    f"Parameter/{name}",
                    par.datatype,
                    control_value,
                    activate_on_control_change=True,
                    update_control_from_edge=True,
                    is_param=True,
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

            # Call the param callback once to initialize the param

            try:
                param_callback(
                    **{
                        name: self.param_ports[f"{self.name}.param.{name}"].get()
                        for name in param.params
                    }
                )
            except Exception:
                logger.warning(
                    f"Error when initializing param {param.name} of node {self.node}:"
                    + traceback.format_exc()
                )

        # hide all ports that are not shown
        for name, port in self.in_ports.get().items():
            if name.split(".in.")[-1] not in self.show_inputs.get():
                port.set_hidden(True)

        for name, port in self.param_ports.get().items():
            if name.split(".param.")[-1] not in self.show_params.get():
                port.set_hidden(True)

        for name, port in self.in_ports.get().items():
            port.on_edge_connected += lambda _, name=name: self._edge_changed(name)
            port.on_edge_disconnected += lambda _, name=name: self._edge_changed(name)

        self.show_inputs.on_set2.add_auto(self.show_inputs_changed)
        self.show_params.on_set2.add_auto(self.show_params_changed)

    def _edge_changed(self, changed_port_name: str):
        changed_port_name = changed_port_name.split(".")[-1]
        for func in self.node_funcs.values():
            if changed_port_name in func.inputs:
                if f"{self.name}.tr.{func.name}" in self.tr_ports:
                    trigger_port = self.tr_ports[f"{self.name}.tr.{func.name}"]
                    trigger_port.set_hidden(not self.needs_trigger_port(func))

    def needs_trigger_port(self, func: NodeFunc):
        for input_name in func.inputs:
            if len(self.in_ports[f"{self.name}.in.{input_name}"].edges) > 0:
                return False
        return True

    def show_inputs_changed(self, old, new):
        old = set(old)
        new = set(new)
        for name in old - new:
            self.in_ports[f"{self.name}.in.{name}"].set_hidden(True)

        for name in new - old:
            self.in_ports[f"{self.name}.in.{name}"].set_hidden(False)

    def show_params_changed(self, old, new):
        old = set(old)
        new = set(new)
        for name in old - new:
            self.param_ports[f"{self.name}.param.{name}"].set_hidden(True)

        for name in new - old:
            self.param_ports[f"{self.name}.param.{name}"].set_hidden(False)

    def add_input_or_param_port(
        self,
        name: str,
        display_name: str,
        editor_display_name: str,
        gtype: GType,
        control_value: Any,
        activate_on_control_change: bool,
        update_control_from_edge: bool,
        is_param: bool,
    ) -> "InputPort":
        control_kwargs: dict[str, Any] = {}
        editor_args: dict[str, Any] = {}

        if gtype == AnyType:
            control_type = ObjectControl
            editor_type = "text"
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
            editor_type = "float"
        elif isinstance(gtype, LiteralType):
            control_type = OptionControl
            control_kwargs["options"] = list(gtype.values)
            editor_type = "options"
            editor_args["options"] = list(gtype.values)

        elif gtype >> None:
            control_type = ButtonControl
            editor_type = "button"

        else:
            # logger.warning(
            #     f"Not support gtype {gtype} for port {name} yet. Will not add control."
            # )
            control_type = ObjectControl
            editor_type = "text"
        # TODO: add more control types

        port = self.node.add_in_port(
            name,
            1,
            display_name=display_name,
            datatype=gtype,
            control_type=control_type,
            control_value=control_value,
            activate_on_control_change=activate_on_control_change,
            update_control_from_edge=update_control_from_edge,
            is_param=is_param,
            **control_kwargs,
        )
        if editor_type is not None:
            self.node.expose_attribute(
                port.default_control.get_value_topic(),
                editor_type,
                display_name=editor_display_name,
                **editor_args,
            )
        return port

    def port_activated(self, port: InputPort):
        port_info = self.port_info_dict[port.get_name()]

        # If the port is a trigger port, run the corresponding node_func
        if port.get_name().startswith(f"{self.name}.tr."):
            port.clear_edges()
            func_name = port.get_name().split(".")[-1]
            node_func = self.node_funcs[func_name]
            if not self.needs_trigger_port(node_func):
                return
            peeked_ports = self.run_node_func(node_func)
            for peeked_port in peeked_ports:
                peeked_port.clear_edges()

        # If the port is a input port, check if all inputs are ready to run the corresponding node_func
        elif port_info.is_func:
            peeked_ports: set[InputPort] = set()
            for node_func in port_info.used_by_funcs:
                # A func requires all its inputs to be ready before it can be executed
                if all(
                    self.in_ports[f"{self.name}.in.{name}"].is_all_ready()
                    for name in node_func.inputs
                ):
                    peeked_ports |= self.run_node_func(node_func)

            for peeked_port in peeked_ports:
                peeked_port.clear_edges()

        elif not port_info.is_func:  # If the port is a param port
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

    def run_node_func(self, node_func: NodeFunc):
        peeked_ports: set[InputPort] = set()
        func = getattr(self.node, node_func.name)
        try:
            inputs = {
                input_name: self.in_ports[f"{self.name}.in.{input_name}"].peek()
                for input_name in node_func.inputs
            }
        except Exception as e:
            self.node.print_exception(e)

        for name in node_func.inputs:
            peeked_ports.add(self.in_ports[f"{self.name}.in.{name}"])
        if node_func.spec.background:
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
                node_func=node_func: self.func_finished(func(**inputs), node_func),
                background=False,
            )
        return peeked_ports

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

    def set_input(self, name, value):
        self.in_ports[f"{self.name}.in.{name}"].set_control_value(value)

    def set_param(self, name, value):
        self.param_ports[f"{self.name}.param.{name}"].set_control_value(value)


def consistent_annotations(annotations: "list[type]") -> bool:
    annotations = [a for a in annotations if a is not AnyType]

    if len(annotations) == 0:
        return True

    first_annotation = annotations[0]
    for annotation in annotations:
        if annotation != first_annotation:
            return False

    return True


def consistent_default_values(defaults: "list[Any]") -> bool:
    defaults = [d for d in defaults if d is not NO_DEFAULT]

    if len(defaults) == 0:
        return True

    first_default = defaults[0]
    for default in defaults[1:]:
        if default != first_default:
            return False

    return True


def iterate_sign_sources(
    sign_sources: Iterable[Callable | inspect.Parameter],
) -> Iterable[tuple[str, inspect.Parameter]]:
    for sign_source in sign_sources:
        if isinstance(sign_source, inspect.Parameter):
            yield sign_source.name, sign_source
            continue
        signature = inspect.signature(sign_source)
        for param_item_name, arg in signature.parameters.items():
            if param_item_name == "self":
                continue
            # filter out *args and **kwargs
            if arg.kind in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }:
                continue
            yield param_item_name, arg


def collect_input_output_params(
    funcs: dict[str, NodeFuncSpec], param_funcs: "dict[str, NodeParamSpec]"
) -> tuple[
    dict[str, list[Input]],
    dict[str, list[Output]],
    dict[str, list[ParamItem]],
    dict[str, NodeFunc],
    dict[str, NodeParam],
]:
    inputs = defaultdict(list[Input])
    outputs = defaultdict(list[Output])
    params = defaultdict(list[ParamItem])
    node_funcs: dict[str, NodeFunc] = {}
    node_params: dict[str, NodeParam] = {}
    for func in funcs.values():
        cur_inputs: dict[str, Input] = {}
        cur_outputs: dict[str, Output] = {}
        # get the first callable in sign_source

        for sign_source in func.sign_source:
            if not isinstance(sign_source, inspect.Parameter):
                fisrt_callable = sign_source
                break
        else:
            raise ValueError(
                f"Please at least provide one function in sign_source for function `{func.name}`."
            )

        if not hasattr(fisrt_callable, "__annotations__"):
            raise ValueError(
                f"Cannot get __annotations__ from function `{fisrt_callable.__name__}`. Please provide a function with annotations for sign_source."
            )
        if "return" in fisrt_callable.__annotations__:
            if "return" in func.annotation_override:
                datatype = GType.from_annotation(func.annotation_override["return"])
            else:
                datatype = GType.from_annotation(
                    fisrt_callable.__annotations__["return"]
                )
        else:
            datatype = AnyType

        out = Output(func.name, datatype)
        outputs[func.name].append(out)
        cur_outputs[func.name] = out

        for arg_name, arg in iterate_sign_sources(func.sign_source):
            if arg_name == "self":
                continue

            if arg_name in func.annotation_override:
                datatype = GType.from_annotation(func.annotation_override[arg_name])
            else:
                datatype = GType.from_annotation(arg.annotation)

            if arg_name in func.default_override:
                default = func.default_override[arg_name]
            else:
                default = (
                    arg.default
                    if arg.default != inspect.Parameter.empty
                    else NO_DEFAULT
                )
            if default is ...:
                default = NO_DEFAULT

            if isinstance(func.shown_ports, SHOW_ALL_PORTS_T):
                show_port_by_default = True
            else:
                show_port_by_default = arg_name in func.shown_ports

            inp = Input(
                name=arg_name,
                datatype=datatype,
                default=default,
                show_port_by_default=show_port_by_default,
            )
            inputs[arg_name].append(inp)
            cur_inputs[arg_name] = inp

        node_funcs[func.name] = NodeFunc(
            name=func.name,
            inputs=cur_inputs,
            outputs=cur_outputs,
            spec=func,
        )

    for param in param_funcs.values():
        cur_params: dict[str, ParamItem] = {}
        for param_item_name, arg in iterate_sign_sources(param.sign_source):
            if param_item_name in param.annotation_override:
                datatype = GType.from_annotation(
                    param.annotation_override[param_item_name]
                )
            else:
                datatype = GType.from_annotation(arg.annotation)

            if param_item_name in param.default_override:
                default = param.default_override[param_item_name]
            else:
                default = (
                    arg.default
                    if arg.default != inspect.Parameter.empty
                    else NO_DEFAULT
                )
            if default is ...:
                default = NO_DEFAULT

            if isinstance(param.shown_ports, SHOW_ALL_PORTS_T):
                show_port_by_default = True
            else:
                show_port_by_default = param_item_name in param.shown_ports

            par = ParamItem(
                name=param_item_name,
                datatype=datatype,
                default=default,
                show_port_by_default=show_port_by_default,
            )

            params[param_item_name].append(par)
            cur_params[param_item_name] = par

        node_params[param.name] = NodeParam(name=param.name, params=cur_params)

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
        if not consistent_default_values([inp.default for inp in annotations]):
            logger.warning(
                f"Input {name} has inconsistent default values between multiple functions. Plese leave only one default value or make them consistent."
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

        if not consistent_default_values([par.default for par in annotations]):
            logger.warning(
                f"Param {name} has inconsistent default values between multiple functions. Plese leave only one default value or make them consistent."
            )
            return False

    return True


T = TypeVar("T", bound=Input | Output | ParamItem)


def reduce(items: list[T]) -> T:
    """
    Pick the most strict type from a list of inputs, outputs or params.
    """
    for item in items:
        if item.datatype != AnyType:
            return item
    return items[0]


def generate_traits(node_def_info: NodeDefInfo) -> "list[Trait]":
    traits: "list[Trait]" = []

    inputs_dict_list, outputs_dict_list, params_dict_list, node_funcs, node_params = (
        collect_input_output_params(node_def_info.funcs, node_def_info.params)
    )

    if not consistent_input_output_params(
        inputs_dict_list, outputs_dict_list, params_dict_list
    ):
        return []

    # no need of decortrait if there are no node_funcs and node_params
    if len(node_funcs) == 0 and len(node_params) == 0:
        return []

    inputs = {name: reduce(item) for name, item in inputs_dict_list.items()}
    outputs = {name: reduce(item) for name, item in outputs_dict_list.items()}
    params = {name: reduce(item) for name, item in params_dict_list.items()}

    # fill in the actual types for node_funcs and node_params
    for node_func in node_funcs.values():
        node_func.inputs = {name: inputs[name] for name in node_func.inputs}
        node_func.outputs = {name: outputs[name] for name in node_func.outputs}

    for node_param in node_params.values():
        node_param.params = {name: params[name] for name in node_param.params}

    traits.append(DecorTrait(inputs, outputs, params, node_funcs, node_params))
    return traits
