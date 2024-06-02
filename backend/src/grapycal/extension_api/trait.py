import enum
import functools
from typing import TYPE_CHECKING, Callable

from grapycal.sobjects.controls.textControl import TextControl
from grapycal.utils.misc import Action
from objectsync import Topic, SObject, ListTopic

if TYPE_CHECKING:
    from grapycal.sobjects.node import Node


def is_overridden(method, base_class=None):
    if base_class is None:
        base_class = method.__self__.__class__.__mro__[1]
    return method.__func__ is not base_class.__dict__[method.__name__]


class Trait:
    def __init__(self, name: str) -> None:
        self.name = name

    def set_node(self, node: "Node"):
        self.node = node

        # only add the event listeners if the method is overridden, so performance is affected minimally
        if is_overridden(self.build_node, Trait):
            self.node.on_build_node += self.build_node
        if is_overridden(self.init_node, Trait):
            self.node.on_init_node += self.init_node
        if is_overridden(self.port_activated, Trait):
            self.node.on_port_activated += self.port_activated
        if is_overridden(self.double_click, Trait):
            self.node.on_double_click += self.double_click

    def get_info(self):
        return {
            "attr_refs": {
                name: obj.get_name().split("/")[-1]
                for name, obj in self.__dict__.items()
                if isinstance(obj, Topic)
            },
            "sobject_refs": {
                name: obj.get_id()
                for name, obj in self.__dict__.items()
                if isinstance(obj, SObject)
            },
        }

    def restore_from_info(self, info):
        for name, id in info["sobject_refs"].items():
            setattr(self, name, self.node._server.get_object(id))
        for name, ref in info["attr_refs"].items():
            setattr(self, name, self.node.get_attribute(ref))

    def build_node(self):
        """
        called right after Node.build_node()
        """

    def init_node(self):
        """
        called right after Noded.init_node()
        """

    def port_activated(self, port: str):
        """
        called when a port is activated
        """

    def double_click(self):
        """
        called when a node is double clicked
        """


def get_next_number_string(strings):
    numbers = [int(s) for s in strings if s.isdigit()]
    if not numbers:
        return "1"
    return str(max(numbers) + 1)


class SourceTrait(Trait):
    def set_chain(self, chain: "Chain"):
        self.chain = chain

    def output_to_chain(self, out):
        self.chain.input(out)

    def output_to_chain_void(self):
        self.chain.input_void()


class SinkTrait(Trait):
    def input_from_chain(self, inp):
        raise NotImplementedError


class ChainTaskMode(enum.Enum):
    ORIGINAL = enum.auto()
    TASK = enum.auto()
    BACKGROUND = enum.auto()


class Chain:
    def __init__(self, *items: "Trait|Callable") -> None:
        self.items = items
        self.first: SourceTrait = self.items[0]  # type: ignore
        assert isinstance(
            self.first, SourceTrait
        ), f"First item must be a source trait, got {self.first}"
        self.last: SinkTrait = self.items[-1]  # type: ignore
        assert isinstance(
            self.last, SinkTrait
        ), f"Last item must be a sink trait, got {self.last}"
        self.transforms: list[Callable] = []
        for i, transform in enumerate(self.items[1:-1]):
            assert isinstance(
                transform, Callable
            ), f"Item {i+1} must be a callable, got {transform}"
            self.transforms.append(transform)

        self.first.set_chain(self)

        # determine task mode.
        # if any transform has is_background_task, then the whole chain is a background task
        # else, if any transform has is_task, then the whole chain is a task

        self.task_mode = ChainTaskMode.ORIGINAL
        for transform in self.transforms:
            if getattr(transform, "is_background_task", False):
                self.task_mode = ChainTaskMode.BACKGROUND
                break
            if getattr(transform, "is_task", False):
                self.task_mode = ChainTaskMode.TASK

        # the task or background task behavior will be managed by the Chain, so we need to
        # replace the transforms with the original functions if they are wrapped in a task or background task
        def get_orig(func_or_task):
            if hasattr(func_or_task, "original_func"):
                return func_or_task.original_func
            return func_or_task

        self.transforms = [get_orig(transform) for transform in self.transforms]

    def input(self, x):
        node = self.first.node
        if self.task_mode == ChainTaskMode.ORIGINAL:
            self._input(x)
        elif self.task_mode == ChainTaskMode.TASK:
            node._run_directly(functools.partial(self._input, x))
        elif self.task_mode == ChainTaskMode.BACKGROUND:
            node._run_in_background(functools.partial(self._input, x))

    def _input(self, x):
        for transform in self.transforms:
            x = transform(self.first.node, x)
        self.last.input_from_chain(x)

    def input_void(self):
        node = self.first.node
        if self.task_mode == ChainTaskMode.ORIGINAL:
            self._input_void()
        elif self.task_mode == ChainTaskMode.TASK:
            node._run_directly(self._input_void)
        elif self.task_mode == ChainTaskMode.BACKGROUND:
            node._run_in_background(self._input_void)

    def _input_void(self):
        if len(self.transforms) == 0:
            self.last.input_from_chain(None)
        else:
            x = self.transforms[0](self.first.node)
            for transform in self.transforms[1:]:
                x = transform(self.first.node, x)
            self.last.input_from_chain(x)

    def get_traits(self) -> list[Trait]:
        return [self.first, self.last]


class TriggerTrait(SourceTrait):
    def __init__(self, port_name="trigger", name: str = "_trigger") -> None:
        super().__init__(name)
        self.port_name = port_name

    def build_node(self):
        self.node.add_in_port(self.port_name)

    def port_activated(self, port: InputPort):
        port.get_all_available()
        self.node.flash_running_indicator()
        self.output_to_chain_void()

    def double_click(self):
        self.node.flash_running_indicator()
        self.output_to_chain_void()


class InputsTrait(SourceTrait):
    def __init__(
        self,
        ins=[],
        name="_inputs",
        attr_name="_inputs",
        expose_attr: bool = False,
        enable_add_button: bool = False,
        on_all_ready: Callable | None = None,
    ) -> None:
        super().__init__(name)
        self.attr_name = attr_name
        self.ins = ins
        self.expose_attr = expose_attr
        self.enable_add_button = enable_add_button
        self.on_all_ready = Action()
        if on_all_ready is not None:
            self.on_all_ready += on_all_ready

    def build_node(self):
        self.port_names = self.node.add_attribute(
            self.attr_name, ListTopic, editor_type="list" if self.expose_attr else None
        )

        if self.enable_add_button:
            self.add_button = self.node.add_button_control("Add Input")

        if self.node.is_new:
            for name in self.ins:
                self.port_names.insert(name, -1)
                self.add_item(name, -1)
        else:
            for name in self.port_names:
                self.add_item(name, -1)

    def add_button_pressed(self):
        self.port_names.insert(get_next_number_string(self.port_names), -1)

    def init_node(self):
        self.port_names.on_insert.add_auto(self.add_item)
        self.port_names.on_pop.add_auto(self.remove_item)
        if self.enable_add_button:
            self.add_button.on_click += self.add_button_pressed

    def add_item(self, name, position):
        self.node.add_in_port(
            name,
            1,
            display_name="" if self.enable_add_button else name,
            control_type=TextControl,
            activation_mode=TextControl.ActivationMode.NO_ACTIVATION,
        )

    def remove_item(self, name, position):
        self.node.remove_in_port(name)

    def port_activated(self, port: str):
        if all(p.is_all_ready() for p in self.node.in_ports):
            inputs = {p.name.get(): p.get() for p in self.node.in_ports}
            self.on_all_ready.invoke(**inputs)
            self.node.flash_running_indicator()
            self.output_to_chain(inputs)

    def __getitem__(self, idx: int):
        return self.port_names[idx]

    def __len__(self):
        return len(self.port_names)


class OutputsTrait(SinkTrait):
    def __init__(
        self,
        outs=["output"],
        name: str = "_outputs",
        attr_name="_outputs",
        expose_attr: bool = False,
    ) -> None:
        super().__init__(name)
        self.attr_name = attr_name
        self.outs = outs
        self.expose_attr = expose_attr

    def build_node(self):
        self.port_names = self.node.add_attribute(
            self.attr_name, ListTopic, editor_type="list" if self.expose_attr else None
        )

        if self.node.is_new:
            for name in self.outs:
                self.port_names.insert(name, -1)
                self.add_item(name, -1)
        else:
            for name in self.port_names:
                self.add_item(name, -1)

    def init_node(self):
        self.port_names = self.node.get_attribute(self.attr_name, ListTopic)
        self.port_names.on_insert.add_auto(self.add_item)
        self.port_names.on_pop.add_auto(self.remove_item)

    def add_item(self, name, position):
        self.node.add_out_port(name)

    def remove_item(self, name, position):
        self.node.remove_out_port(name)

    def __getitem__(self, idx: int):
        return self.port_names[idx]

    def __len__(self):
        return len(self.port_names)

    def push(self, name, value):
        self.node.get_out_port(name).push(value)

    def input_from_chain(self, inp):
        if len(self.port_names) == 1:
            self.push(self.port_names[0], inp)
        else:
            for name, value in inp.items():
                self.push(name, value)
