import logging
from pprint import pprint

from grapycal.core.background_runner import RunnerInterrupt
from grapycal.core.client_msg_types import ClientMsgTypes
from grapycal.core.typing import GType, AnyType
from grapycal.extension_api.node_def import (
    DecorTrait,
    NodeFuncSpec,
    NodeParamSpec,
    generate_traits,
    get_node_def_info,
)
from grapycal.extension_api.trait import Chain, Trait
from grapycal.sobjects.controls.keyboardControl import KeyboardControl
from grapycal.sobjects.controls.sliderControl import SliderControl
from grapycal.sobjects.controls.toggleControl import ToggleControl
from grapycal.utils.misc import Action, as_type

logger = logging.getLogger(__name__)
import asyncio
import enum
import functools
import io
import traceback
from abc import ABCMeta
from contextlib import contextmanager
from itertools import count
from typing import TYPE_CHECKING, Awaitable, Callable, Literal, Self, TypeVar

from grapycal.extension.utils import NodeInfo
from grapycal.sobjects.controls.buttonControl import ButtonControl
from grapycal.sobjects.controls.codeControl import CodeControl
from grapycal.sobjects.controls.control import Control, ValuedControl
from grapycal.sobjects.controls.imageControl import ImageControl
from grapycal.sobjects.controls.linePlotControl import LinePlotControl
from grapycal.sobjects.controls.nullControl import NullControl
from grapycal.sobjects.controls.optionControl import OptionControl
from grapycal.sobjects.controls.textControl import TextControl
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import UNSPECIFY_CONTROL_VALUE, InputPort, OutputPort, Port
from grapycal.stores import main_store
from grapycal.utils.io import OutputStream
from grapycal.utils.logging import user_logger, warn_extension
from objectsync import (
    DictTopic,
    FloatTopic,
    IntTopic,
    ListTopic,
    ObjDictTopic,
    ObjListTopic,
    SetTopic,
    SObject,
    StringTopic,
    Topic,
)
from objectsync.sobject import SObjectSerialized, WrappedTopic

if TYPE_CHECKING:
    from grapycal.extension.extension import Extension


def warn_no_control_name(control_type, node):
    """
    Log a warning if the control does not have a name.
    """
    node_type = node.get_type_name().split(".")[1]
    warn_extension(
        node,
        f"Consider giving a name to the {control_type.__name__} in {node_type} \
to prevent error when Grapycal auto restores the control.",
        extra={"key": f"No control name {node_type}"},
    )


"""
Decorator for node development.
"""


def singletonNode(auto_instantiate=True):
    """
    Decorator for singleton nodes.
    There can be only one instance of a singleton node in the workspace.
    The instance can be accessed by the `instance` attribute of the class after it is instantiated.
    Raises an error if the node is instantiated more than once.

    Args:
        - auto_instantiate: If set to True, the node will be instantiated (not visible) automatically when the extension is loaded. Otherwise, the user or extension can instantiate the node at any time.

    Example:
    ```
        @singletonNode()
        class TestSingNode(Node):
            category = "test"

    The instance can be accessed by `TestSingNode.instance`.
    ```

    """
    T = TypeVar("T", bound=Node)

    def wrapper(cls: type[T]):
        def new_init(self, *args, **kwargs):
            if hasattr(cls, "instance"):
                raise RuntimeError("Singleton node can only be instantiated once")
            super(cls, self).__init__(*args, **kwargs)
            cls.instance = self

        cls.__init__ = new_init

        def new_destroy(self) -> SObjectSerialized:
            del cls.instance
            return super(cls, self).destroy()

        cls.destroy = new_destroy

        cls._is_singleton = True
        cls._auto_instantiate = auto_instantiate
        return cls

    return wrapper


def deprecated(message: str, from_version: str, to_version: str):
    """
    Decorator for deprecated nodes.
    """

    def wrapper(cls: type[Node]):
        old_init_node = cls.init_node

        def new_init_node(self: Node, **kwargs):
            old_init_node(self, **kwargs)
            self.print_exception(
                RuntimeWarning(
                    f"{cls.__name__} is deprecated from version {from_version}, and will be removed in version {to_version}. {message}"
                )
            )
            user_logger.warning(
                f"{cls.__name__} is deprecated from version {from_version} to {to_version}. {message}"
            )

        cls.init_node = new_init_node

        if cls._deprecated is False:
            cls._deprecated = True
            cls.category = "hidden"
            cls.__doc__ = f"{cls.__doc__}\n\nDeprecated from version {from_version} to {to_version}. {message}"

        return cls

    return wrapper


def background_task(func: Callable):
    """
    A decorator to run a task in the background thread.
    """
    # TODO: If already in the background thread, just run it.

    def wrapper(self: "Node", *args, **kwargs):
        self._run_in_background(functools.partial(func, self, *args, **kwargs))

    wrapper.is_background_task = True
    wrapper.original_func = func
    wrapper.__name__ = func.__name__

    return wrapper


def task(func: Callable):
    """
    A decorator to run a task in the node's context (current thread).
    """

    def wrapper(self: "Node", *args, **kwargs):
        self.incr_n_running_tasks()
        try:
            ret = func(self, *args, **kwargs)
        except Exception as e:
            self._on_exception(e, truncate=1)
            ret = None
        self.decr_n_running_tasks()
        return ret

    wrapper.is_task = True
    wrapper.original_func = func
    wrapper.__name__ = func.__name__

    return wrapper


class NodeMeta(ABCMeta):
    class_def_counter = count()
    def_order = {}

    def __init__(self, name, bases, attrs):
        self.def_order[name] = next(self.class_def_counter)
        self._is_singleton = (
            False  # True if @sigletonNode. Used internally by the ExtensionManager.
        )
        self._auto_instantiate = True  # Used internally by the ExtensionManager.

        # There may be @funcs or @params etc in the base classes. In that case, we need to merge them.
        base_node_def_info = None
        if len(bases) > 0:
            base = bases[0]
            if isinstance(base, NodeMeta):
                base_node_def_info = base._node_def_info

        # used to generate traits out of high level node def interface
        self._node_def_info = get_node_def_info(attrs, base_node_def_info)

        return super().__init__(name, bases, attrs)


class RESTORE_FROM(enum.Enum):
    SAME = 0


class Node(SObject, metaclass=NodeMeta):
    frontend_type = "Node"
    category = "hidden"
    label: str | None = None
    shape = "normal"
    instance: Self  # The singleton instance. Used by singleton nodes.
    _deprecated = False  # TODO: If set to True, the node will be marked as deprecated in the inspector.
    ext: "Extension"
    icon_path: str | None = None
    search = []

    @classmethod
    def get_doc_string(cls):
        return cls.__doc__

    @classmethod
    def get_default_label(cls):
        name = cls.__name__
        name = name[:-4] if name.endswith("Node") else name
        # add space before capital letters except the first one
        return "".join(
            " " + c if c.isupper() and i != 0 else c for i, c in enumerate(name)
        )

    @classmethod
    def set_extension(cls, ext: "Extension"):
        cls.ext = ext

    @classmethod
    def get_def_order(cls):
        return cls.def_order[cls.__name__]

    def initialize(self, serialized: SObjectSerialized | None = None, *args, **kwargs):
        self._already_restored_attributes = set()
        self._already_restored_controls = set()
        self.old_node_info = NodeInfo(serialized) if serialized is not None else None
        self.is_building = False
        self._n_running_tasks = 0

        self.on_build_node = Action()
        self.on_init_node = Action()
        self.on_port_activated = Action()
        self.on_icon_clicked = Action()
        self.on_destroy = Action()

        from grapycal.sobjects.editor import Editor

        parent = self.get_parent()
        if isinstance(parent, Editor):
            self.editor = parent
        else:
            self.editor = None

        trait_list: list[Trait] = []

        trait_list += self.define_traits_gen()

        define_traits_output = self.define_traits()
        if isinstance(define_traits_output, list):
            for item in define_traits_output:
                if isinstance(item, Trait):
                    trait_list.append(item)
                elif isinstance(item, Chain):
                    trait_list.extend(item.get_traits())
                else:
                    raise ValueError("Invalid trait")
        elif isinstance(define_traits_output, Trait):
            trait_list.append(define_traits_output)
        elif isinstance(define_traits_output, Chain):
            trait_list.extend(define_traits_output.get_traits())
        else:
            raise ValueError("Invalid trait")

        self.traits: dict[str, Trait] = {}
        for item in trait_list:
            assert (
                item.name not in self.traits
            ), f"duplicate trait name {item.name}. Please specify the traits' names to make them different"
            self.traits[item.name] = item
            item.set_node(self)
        super().initialize(serialized, *args, **kwargs)

    def define_traits_gen(self) -> list[Trait]:
        # self._node_def_info.funcs.update(self.define_funcs())
        # self._node_def_info.params.update(self.define_params())
        for func in self.define_funcs():
            self._node_def_info.funcs[func.name] = func
        for param in self.define_params():
            self._node_def_info.params[param.name] = param
        try:
            return generate_traits(self._node_def_info)
        except Exception as e:
            raise RuntimeError(
                f"Failed to define node type {self.get_type_name()}: {e}"
            )

    def define_traits(self) -> list[Trait | Chain] | Trait | Chain:
        return []

    def build(
        self,
        is_preview=False,
        translation="0,0",
        is_new=True,
        old_node_info: NodeInfo | None = None,
        input_values=None,
        param_values=None,
        **build_node_args,
    ):
        self.is_new = is_new
        self.old_node_info = old_node_info
        self.is_building = True

        # DecorTrait reads input_values and param_values
        self.input_values = input_values or {}
        self.param_values = param_values or {}

        self.shape_topic = self.add_attribute(
            "shape", StringTopic, self.shape
        )  # normal, simple, round
        self.output_topic = self.add_attribute(
            "output", ListTopic, [], is_stateful=False, restore_from=None
        )
        self.label_topic = self.add_attribute(
            "label",
            StringTopic,
            self.label if self.label is not None else self.get_default_label(),
            is_stateful=False,
            restore_from=None,
        )
        self.label_offset = self.add_attribute(
            "label_offset", FloatTopic, 0, restore_from=None
        )
        self.translation = self.add_attribute(
            "translation",
            StringTopic,
            translation
            if isinstance(translation, str)
            else ",".join(map(str, translation)),
        )
        self.is_preview = self.add_attribute(
            "is_preview", IntTopic, 1 if is_preview else 0, restore_from=None
        )
        self.category_ = self.add_attribute(
            "category", StringTopic, self.category, restore_from=None
        )
        self.exposed_attributes = self.add_attribute(
            "exposed_attributes", ListTopic, [], restore_from=None
        )
        self.globally_exposed_attributes = self.add_attribute(
            "globally_exposed_attributes", DictTopic, restore_from=None
        )
        self.css_classes = self.add_attribute(
            "css_classes", SetTopic, [], restore_from=None
        )
        self.icon_path_topic = self.add_attribute(
            "icon_path",
            StringTopic,
            f"{self.__class__.__name__[:-4].lower()}"
            if self.icon_path is None
            else self.icon_path,
            is_stateful=False,
            restore_from=None,
        )

        self.expose_attribute(
            self.shape_topic,
            display_name="Apparance/shape",
            editor_type="options",
            options=["normal", "simple", "round"],
        )

        # for inspector
        self.type_topic = self.add_attribute(
            "type", StringTopic, self.get_type_name(), restore_from=None
        )

        self.in_ports = self.add_attribute(
            "in_ports", ObjListTopic[InputPort], restore_from=None
        )
        self.out_ports = self.add_attribute(
            "out_ports", ObjListTopic[OutputPort], restore_from=None
        )

        self.controls = self.add_attribute(
            "controls", ObjDictTopic[Control], restore_from=None
        )

        # store these info in the node's serialized data so when restoring, traits can be restored
        self.traits_info = self.add_attribute(
            "traits_info",
            DictTopic,
            is_stateful=False,
        )

        # some traits may need to access the build_node_args
        self.build_node_args = build_node_args

        self.on_build_node.invoke()  # not passing build_node_args because traits should be independent of the node type
        self.build_node(**build_node_args)
        self.is_building = False

        # store traits info
        trait_info = {}
        for trait in self.traits.values():
            trait_info[trait.name] = trait.get_info()
        self.traits_info.set(trait_info)

    def define_funcs(self) -> list[NodeFuncSpec]:
        """
        Put node functions here. This is a more dynamic way to define node functions than using the @func decorator.
        """
        return []

    def define_params(self) -> list[NodeParamSpec]:
        """
        Put node parameters here. This is a more dynamic way to define node parameters than using the @param decorator.
        """
        return []

    def get_decor_trait(self) -> DecorTrait:
        return as_type(self.traits["_decor"], DecorTrait)

    def set_input(self, name, value):
        self.get_decor_trait().set_input(name, value)

    def set_param(self, name, value):
        self.get_decor_trait().set_param(name, value)

    def build_node(self):
        """
        Create attributes, ports, and controls here.

        Note:
            This method will not be called when the object is being restored. The child objects will be restored automatically instead of
        running this method again.
        """

    def init(self):
        self.on("icon_clicked", self.icon_clicked, is_stateful=False)
        self.on("icon_clicked", self.on_icon_clicked.invoke, is_stateful=False)
        self.on("spawn", self.spawn, is_stateful=False)

        self._output_stream: OutputStream | None = None

        self.globally_exposed_attributes.on_add.add_auto(
            lambda k, v: main_store.settings.entries.add(k, v)
        )
        for k, v in self.globally_exposed_attributes.get().items():
            main_store.settings.entries.add(k, v)

        # restore traits
        trait_info = self.traits_info.get()
        for name, trait in self.traits.items():
            trait.restore_from_info(trait_info[name])

        self.on_init_node.invoke()
        self.init_node()

    def init_node(self):
        """
        This method is called after the node is built and its ports and controls are created. Use this method if you want to do something after
        the node is built.

        Do not affect other nodes' attributes, controls, or ports or create/destroy other nodes in this method. Use post_create() for that purpose.
        """
        pass

    def restore_from_version(self, version: str, old: NodeInfo):
        """
        DEPRECATED from v0.11.0: Restoration of attributes and controls should be done in build() via therestore_from argument in add_attribute and add_control.
        """

    def restore_attributes(self, *attribute_names: str | tuple[str, str]):
        """
        You can call it in the `restore` method to restore attributes from the old node.
        For each entry in `attribute_names`, if it's a string, the attribute with the same name will be restored from the old node. If it's a tuple, the first element is the name of the attribute in the old node, and the second element is the name of the attribute in the new node.

        Example:
        ```
        def restore(self,version,old):
            self.restore_attributes('position,'rotation')
            self.restore_attributes(('old_name1','new_name1'),('old_name2','new_name2'))
        ```
        """
        if self.is_new or not self.is_building:
            return
        for name in attribute_names:
            if isinstance(name, tuple):
                old_name, new_name = name
            else:
                old_name, new_name = name, name

            if new_name in self._already_restored_attributes:
                continue
            self._already_restored_attributes.add(new_name)

            if not self.has_attribute(new_name):
                warn_extension(
                    self,
                    f"Attribute {new_name} does not exist in {self}",
                    extra={"key": f"Attribute not exist {self.get_type_name()}"},
                )
                continue
            if not self.old_node_info.has_attribute(old_name):
                warn_extension(
                    self,
                    f"Attribute {old_name} does not exist in the old node of {self}",
                    extra={"key": f"Attribute not exist old {self.get_type_name()}"},
                )
                continue
            new_attr = self.get_attribute(new_name)
            old_attr = self.old_node_info[old_name]  # type: ignore # not self.is_new grarauntees old_node_info is not None
            try:  # Validator may fail and raise an exception.
                if isinstance(new_attr, WrappedTopic):
                    new_attr.set_raw(old_attr)
                else:
                    new_attr.set(old_attr)
            except Exception:
                logger.warning(f"Failed to restore attribute {new_name} in {self}")

    def restore_controls(self, *control_names: str | tuple[str, str]):
        """
        Recover controls from the old node.
        """
        if self.is_new or not self.is_building:
            return
        assert self.old_node_info is not None
        for name in control_names:
            if isinstance(name, tuple):
                old_name, new_name = name
            else:
                old_name, new_name = name, name

            # DEPRECATED from v0.11.0: this check is for backward compatibility.
            if new_name in self._already_restored_controls:
                continue
            self._already_restored_controls.add(new_name)

            if new_name not in self.controls:
                warn_extension(
                    self,
                    f"Control {new_name} does not exist in {self}",
                    extra={
                        "key": f"Control not exist {self.get_type_name()} {new_name}"
                    },
                )
                continue
            if old_name not in self.old_node_info.controls:
                warn_extension(
                    self,
                    f"Control {old_name} does not exist in the old node of {self}",
                    extra={
                        "key": f"Control not exist old {self.get_type_name()} {old_name}"
                    },
                )
                continue
            try:
                self.controls[new_name].restore_from(
                    self.old_node_info.controls[old_name]
                )
            except Exception:
                self.efagrwthnh = ""

    def post_create(self):
        """
        Called after the node is created and restored. Use it for affecting other nodes during the creation process. "Affecting" means creating or destroying other nodes, or modifying other nodes' attributes, controls, or ports.

        It will not be called when the node is restored from undo/redo because if so, other nodes will be affected twice.
        """

    def spawn(self, client_id):
        """
        Called when a client wants to spawn a node.
        """
        new_node = main_store.main_editor.create_node(type(self), sender=client_id)
        if new_node is None:  # failed to create node
            return
        new_node.add_tag(
            f"drag_created_by{client_id}"
        )  # So the client can find the node it spawned and make it follow the mouse

    def attach_to_port(self, other_port: Port):
        if isinstance(other_port, InputPort):
            if len(self.out_ports) == 0:
                return
            self_port = self.out_ports[0]
            assert self_port is not None
            self.editor.create_edge(self_port, other_port)
        elif isinstance(other_port, OutputPort):
            if len(self.in_ports) == 0:
                return
            self_port = self.in_ports[0]
            assert self_port is not None
            self.editor.create_edge(other_port, self_port)

    def destroy(self) -> SObjectSerialized:
        """
        Called when the node is destroyed. You can override this method to do something before the node is destroyed.
        Note: Overrided methods should call return super().destroy() at the end.
        """
        self.on_destroy.invoke()
        if self._output_stream is not None:
            self._output_stream.close()
        for port in self.in_ports:
            if len(port.edges) > 0:
                raise RuntimeError(
                    f"Trying to destroy node {self.get_id()} but it still has input edges"
                )
        for port in self.out_ports:
            if len(port.edges) > 0:
                raise RuntimeError(
                    f"Trying to destroy node {self.get_id()} but it still has output edges"
                )
        for name in self.globally_exposed_attributes.get():
            main_store.settings.entries.pop(name)

        if self.editor is not None:
            self.editor.is_running_manager.set_running(self, False)
        return super().destroy()

    T = TypeVar("T", bound=ValuedControl)

    def add_in_port(
        self,
        name: str,
        max_edges=64,
        display_name=None,
        control_type: type[T] = NullControl,
        control_name=None,
        control_value=UNSPECIFY_CONTROL_VALUE,
        restore_from: str | None | RESTORE_FROM = RESTORE_FROM.SAME,
        datatype: GType = AnyType,
        activate_on_control_change=False,
        update_control_from_edge=False,
        is_param=False,
        **control_kwargs,
    ) -> InputPort[T]:
        """
        Add an input port to the node.
        If control_type is not None, a control will be added to the port. It must be a subclass of ValuedControl.
        When no edges are connected to the port, the control will be used to get the data.
        """
        if control_name is None:
            control_name = name
        port = self.add_child(
            InputPort,
            control_type=control_type,
            name=name,
            max_edges=max_edges,
            display_name=display_name,
            control_name=control_name,
            control_value=control_value,
            datatype=datatype,
            activate_on_control_change=activate_on_control_change,
            update_control_from_edge=update_control_from_edge,
            is_param=is_param,
            **control_kwargs,
        )
        self.in_ports.insert(port)
        if control_type is NullControl:
            control_name = None
        if control_name is not None:
            if control_name in self.controls:
                raise ValueError(f"Control with name {control_name} already exists")
        else:
            control_name = "Control0"
            i = 0
            while control_name in self.controls:
                i += 1
                control_name = f"Control{i}"

        self.controls.add(control_name, port.default_control)
        if control_type is not NullControl:
            if restore_from == RESTORE_FROM.SAME:
                self.restore_controls(name)
            elif restore_from is None:
                pass
            else:
                self.restore_controls((restore_from, name))
        return port

    def add_out_port(
        self, name: str, max_edges=64, display_name=None, datatype: GType = AnyType
    ):
        """
        Add an output port to the node.
        """
        port = self.add_child(
            OutputPort,
            name=name,
            max_edges=max_edges,
            display_name=display_name,
            datatype=datatype,
        )
        self.out_ports.insert(port)
        return port

    def remove_in_port(self, name: str):
        """
        Remove an input port from the node.
        """
        # find the port with the given name
        for port in self.in_ports:
            assert port is not None
            if port.name.get() == name:
                break
        else:
            raise ValueError(f"Port with name {name} does not exist")

        # remove all edges connected to the port
        for edge in port.edges[:]:
            edge.remove()  # do this in port.remove()?

        # remove the port
        self.in_ports.remove(port)
        self.controls.remove(port.default_control)
        port.remove()

    def remove_out_port(self, name: str):
        """
        Remove an output port from the node.
        """
        # find the port with the given name
        for port in self.out_ports:
            assert port is not None
            if port.name.get() == name:
                break
        else:
            raise ValueError(f"Port with name {name} does not exist")

        # remove all edges connected to the port
        for edge in port.edges[:]:
            edge.remove()  # do this in port.remove()?

        # remove the port
        self.out_ports.remove(port)
        port.remove()

    def get_in_port(self, name: str) -> InputPort:
        """
        Get an input port by its name.
        """
        for port in self.in_ports:
            assert port is not None
            if port.name.get() == name:
                return port
        raise ValueError(f"Port with name {name} does not exist")

    def get_out_port(self, name: str) -> OutputPort:
        """
        an output port by its name.
        """
        for port in self.out_ports:
            assert port is not None
            if port.name.get() == name:
                return port
        raise ValueError(f"Port with name {name} does not exist")

    def has_in_port(self, name: str) -> bool:
        """
        Check if an input port exists.
        """
        for port in self.in_ports:
            assert port is not None
            if port.name.get() == name:
                return True
        return False

    def has_out_port(self, name: str) -> bool:
        """
        Check if an output port exists.
        """
        for port in self.out_ports:
            assert port is not None
            if port.name.get() == name:
                return True
        return False

    T = TypeVar("T", bound=Control)

    def add_control(
        self,
        control_type: type[T],
        name: str | None = None,
        restore_from: str | None | RESTORE_FROM = RESTORE_FROM.SAME,
        **kwargs,
    ) -> T:
        """
        Add a control to the node.
        """
        if name is not None:
            if name in self.controls:
                raise ValueError(f"Control with name {name} already exists")
        else:
            if control_type not in [ButtonControl] and restore_from is not None:
                warn_no_control_name(control_type, self)
            name = "Control0"
            i = 0
            while name in self.controls:
                i += 1
                name = f"Control{i}"

        control = self.add_child(control_type, **kwargs)
        self.controls.add(name, control)

        # restore the control
        if restore_from == RESTORE_FROM.SAME:
            self.restore_controls(name)
        elif restore_from is None:
            pass
        else:
            self.restore_controls((restore_from, name))

        return control

    def add_text_control(
        self,
        text: str = "",
        label: str = "",
        readonly=False,
        editable: bool = True,
        name: str | None = None,
        placeholder: str = "",
    ) -> TextControl:
        """
        Add a text control to the node.
        """
        control = self.add_control(
            TextControl,
            text=text,
            label=label,
            readonly=readonly,
            editable=editable,
            name=name,
            placeholder=placeholder,
        )
        return control

    def add_button_control(
        self, label: str = "", name: str | None = None
    ) -> ButtonControl:
        """
        Add a button control to the node.
        """
        control = self.add_control(ButtonControl, label=label, name=name)
        return control

    def add_image_control(self, name: str | None = None) -> ImageControl:
        """
        Add an image control to the node.
        """
        control = self.add_control(ImageControl, name=name)
        return control

    def add_lineplot_control(self, name: str | None = None) -> LinePlotControl:
        """
        Add a line plot control to the node.
        """
        control = self.add_control(LinePlotControl, name=name)
        return control

    def add_option_control(
        self, value: str, options: list[str], label: str = "", name: str | None = None
    ) -> OptionControl:
        """
        Add an option control to the node.
        """
        control = self.add_control(
            OptionControl, value=value, options=options, label=label, name=name
        )
        return control

    def add_keyboard_control(self, label: str = "") -> KeyboardControl:
        """
        Add a keyboard control to the node.
        """
        control = self.add_control(KeyboardControl, label=label)
        return control

    def add_slider_control(
        self,
        label: str = "",
        value: float = 0,
        min: float = 0,
        max: float = 1,
        step: float = 0.01,
        int_mode: bool = False,
        name: str | None = None,
    ) -> SliderControl:
        """
        Add a slider control to the node.
        """
        control = self.add_control(
            SliderControl,
            label=label,
            value=value,
            min=min,
            max=max,
            step=step,
            int_mode=int_mode,
            name=name,
        )
        return control

    def add_code_control(
        self,
        text: str = "",
        label: str = "",
        readonly=False,
        editable: bool = True,
        name: str | None = None,
        placeholder: str = "",
    ) -> CodeControl:
        """
        Add a code control to the node.
        """
        control = self.add_control(
            CodeControl,
            text=text,
            label=label,
            readonly=readonly,
            editable=editable,
            name=name,
            placeholder=placeholder,
        )
        return control

    def add_toggle_control(
        self, value: bool = False, label: str = "", name: str | None = None
    ):
        """
        Add a toggle control to the node.
        """
        control = self.add_control(ToggleControl, value=value, label=label, name=name)
        return control

    def remove_control(self, control: str | Control):
        if isinstance(control, str):
            control = self.controls[control]
        self.controls.remove(control)
        control.remove()

    # Wrap the SObject.addattribute() to make shorthand of exposing attributes after adding them.
    T1 = TypeVar("T1", bound=Topic | WrappedTopic)

    def add_attribute(
        self,
        topic_name: str,
        topic_type: type[T1],
        init_value=None,
        is_stateful=True,
        editor_type: str | None = None,
        display_name: str | None = None,
        target: Literal["self", "global"] = "self",
        order_strict: bool | None = None,
        restore_from: str | None | RESTORE_FROM = RESTORE_FROM.SAME,
        **editor_args,
    ) -> T1:
        """
        Add an attribute to the node.

        Args:
            - topic_name: The name of the attribute. Has to be unique in the node.
            - topic_type: The type of the attribute. Can be one of the following: StringTopic, IntTopic, FloatTopic, ListTopic, DictTopic, SetTopic, ObjTopic, ObjListTopic, ObjDictTopic, ObjSetTopic.
            - init_value: The initial value of the attribute. If set to None, the attribute will be initialized with the default value of the topic type.
            - is_stateful: If set to True, the changes to the attribute will be stored in the history and can be undone or redone. If set to False, the changes will not be stored.
            - editor_type, display_name, target, and editor_args: If editor_type is not None, the attribute will be exposed to the inspector. Please see Node.expose_attribute() for details.
            - order_strict: If set to True, the changes to the attribute won't be merged or reordered with other changes for communication efficiency. If set to None, it will be set to the same as is_stateful.
            - restore_from: The name of the attribute to restore from. If set to None, the attribute will restore from the attribute with the same name in the old node. If set to False, the attribute will not be restored. To restore an attribute based on different source version, see Node.restore().
        """

        if order_strict is None:
            order_strict = is_stateful

        attribute = super().add_attribute(
            topic_name, topic_type, init_value, is_stateful, order_strict=order_strict
        )
        if editor_type is not None:
            self.expose_attribute(
                attribute, editor_type, display_name, target=target, **editor_args
            )
        if restore_from == RESTORE_FROM.SAME:
            self.restore_attributes(topic_name)
        elif restore_from is None:
            pass
        else:
            self.restore_attributes((restore_from, topic_name))
        return attribute

    def expose_attribute(
        self,
        attribute: Topic | WrappedTopic,
        editor_type,
        display_name=None,
        target: Literal["self", "global"] = "self",
        **editor_args,
    ):
        """
        Expose an attribute to the inspector.

        Args:
            - attribute: The attribute to expose.

            - editor_type: The type of the editor to use. Can be ``text``, ``list``, ``int``, ``float``,  ``button``, ``options``, or ``dict``.

            - display_name: The name to display in the editor. If not specified, the attribute's name will be used.

            - target: The target of the attribute. Can be ``self`` or ``global``. If set to ``self``, the attribute will be exposed to the inspector of the node. If set to ``global``, the attribute will be exposed to the global settings tab.

            - **editor_args: The arguments to pass to the editor. See below for details.


        There are 2 ways to expose an attribute:
        1. Call this method. For example:
            ```
            my_attr = self.add_attribute('my_attr',ListTopic,[])
            self.expose_attribute(my_attr,'list')
            ```
        2. Call the `add_attribute` method with the `editor_type` argument. For example:
            ```
            my_attr = self.add_attribute('my_attr',ListTopic,[],editor_type='list')
            ```

        Both ways are equivalent.

        List of editor types:
            - ``dict``: A dictionary editor. Goes with a DictTopic. editor_args:

            ```
            {
                'key_options':list[str]|None,
                'value_options':list[str]|None,
                'key_strict':bool|None,
                'value_strict':bool|None,
            }
            ```

            - ``list``: A list editor. Goes with a ListTopic. editor_args: `{}`

            - ``options``: A dropdown editor. Goes with a StringTopic. editor_args:

            ```
            {
                'options':list[str],
            }
            ```

            - ``text``: A text editor. Goes with a StringTopic. editor_args: `{}`

            - ``int``: An integer editor. Goes with an IntTopic. editor_args: `{}`

            - ``float``: A float editor. Goes with a FloatTopic. editor_args: `{}`
        """
        if editor_args is None:  # not stepping into the dangerous trap of Python :D
            editor_args = {}
        name = attribute.get_name()
        if display_name is None:
            display_name = name.split("/")[-1]
        editor_args["type"] = editor_type

        if target == "self":
            self.exposed_attributes.insert(
                {"name": name, "display_name": display_name, "editor_args": editor_args}
            )
        elif target == "global":
            self.globally_exposed_attributes.add(
                name,
                {
                    "name": name,
                    "display_name": display_name,
                    "editor_args": editor_args,
                },
            )
        else:
            raise ValueError(f"Invalid target {target}")

    def print(self, *objs, sep=" ", end="\n", **kwargs):
        """
        Print to the node's output.
        """
        # print(*args,**kwargs,file=self._output_stream)
        # self._output_stream.flush()

        # maybe the self._output_stream can be abandoned
        output = io.StringIO(newline="")
        for obj in objs[:-1]:
            if isinstance(obj, str):
                output.write(obj)
            else:
                pprint(obj, stream=output, **kwargs)
            output.write(sep)
        pprint(objs[-1], stream=output, **kwargs)
        output.write(end)
        contents = output.getvalue()
        output.close()

        self.raw_print(contents)

    def raw_print(self, data):
        if data == "":
            return
        if self.is_destroyed():
            logger.debug(
                f"Output received from a destroyed node {self.get_id()}: {data}"
            )
        else:
            if len(self.output_topic) > 100:
                self.output_topic.set([])
                self.output_topic.insert(["error", "Too many output lines. Cleared.\n"])
            self.output_topic.insert(["output", data])

    def get_position(self, translation: list[float]):
        """
        Get the position of the node.
        """
        position = self.translation.get().split(",")
        return [
            float(position[0]) + translation[0],
            float(position[1]) + translation[1],
        ]

    """
    Run tasks in the background or foreground, redirecting stdout to the node's output stream.
    """

    @contextmanager
    def _redirect_output(self):
        """
        Returns a context manager that redirects stdout to the node's output stream.
        """

        # create the output stream if it doesn't exist
        if self._output_stream is None:
            self._output_stream = OutputStream(self.raw_print)
            self._output_stream.set_event_loop(main_store.event_loop)
            main_store.event_loop.create_task(self._output_stream.run())

        try:
            self._output_stream.enable_flush()
            with main_store.redirect(self._output_stream):
                yield
        finally:
            self._output_stream.disable_flush()

    def _on_exception(self, e: Exception, truncate=2):
        if isinstance(e, RunnerInterrupt):
            main_store.send_message_to_all(
                "Runner interrupted by user.", ClientMsgTypes.BOTH
            )
        else:
            self.print_exception(e, truncate=truncate)
        main_store.clear_edges_and_tasks()

    def _run_in_background(
        self, task: Callable[[], None], to_queue=True, redirect_output=False
    ):
        """
        Run a task in the background thread.
        """

        def wrapped():
            self.incr_n_running_tasks()
            try:
                if redirect_output:
                    with self._redirect_output():
                        ret = task()
                else:
                    ret = task()
            except Exception:
                self.decr_n_running_tasks()
                raise
            self.decr_n_running_tasks()
            return ret

        main_store.runner.push(
            wrapped, to_queue=to_queue, exception_callback=self._on_exception
        )

    def _run_directly(self, task: Callable[[], None], redirect_output=False):
        """
        Run a task in the current thread.
        """
        self.incr_n_running_tasks()
        try:
            if redirect_output:
                with self._redirect_output():
                    task()
            else:
                task()
        except Exception as e:
            self._on_exception(e, truncate=1)
        self.decr_n_running_tasks()

    def _run_async(self, task: Callable[[], Awaitable[None]]):
        """
        Run an async task.
        """

        async def wrapped():
            self.incr_n_running_tasks()
            try:
                await task()
            except Exception as e:
                self._on_exception(e, truncate=1)
            self.decr_n_running_tasks()

        main_store.event_loop.create_task(wrapped())

    def incr_n_running_tasks(self):
        self._n_running_tasks += 1
        if self._n_running_tasks == 1:
            self.set_running(True)

    def decr_n_running_tasks(self):
        self._n_running_tasks -= 1
        if self._n_running_tasks == 0:
            self.set_running(False)

    def run(
        self,
        task: Callable,
        background=True,
        to_queue=True,
        redirect_output=False,
        *args,
        **kwargs,
    ):
        """
        Run a task in the node's context i.e. the stdout and errors will be redirected to the node's output attribute and be displayed in front-end.

        Args:
            - task: The task to run.

            - background: If set to True, the task will be scheduled to run in the background thread. Otherwise, it will be run in the current thread immediately.

            - to_queue: This argument is used only when `background` is True. If set to True, the task will be pushed to the :class:`.BackgroundRunner`'s queue.\
            If set to False, the task will be pushed to its stack. See :class:`.BackgroundRunner` for more details.
        """
        is_async = asyncio.iscoroutinefunction(task)
        task = functools.partial(task, *args, **kwargs)
        if is_async:
            self._run_async(task)
        elif background:
            self._run_in_background(task, to_queue, redirect_output=False)
        else:
            self._run_directly(task, redirect_output=False)

    def print_exception(self, e: Exception | str, truncate=0, clear_graph=False):
        if isinstance(e, str):
            message = e
        else:
            message = "".join(traceback.format_exception(e)[truncate:])
        if self.is_destroyed():
            logger.warning(
                f"Exception occured in a destroyed node {self.get_id()}: {message}"
            )
        else:
            if len(self.output_topic) > 100:
                self.output_topic.set([])
                self.output_topic.insert(["error", "Too many output lines. Cleared.\n"])
            self.output_topic.insert(["error", message])

        if clear_graph:
            main_store.clear_edges_and_tasks()

    def flash_running_indicator(self):
        self.incr_n_running_tasks()
        self.decr_n_running_tasks()

    def set_running(self, running: bool):
        if self.is_preview.get() == 1:
            return
        with self._server.record(
            allow_reentry=True
        ):  # aquire the lock to prevent setting the attribute while the sobject being deleted
            if self.is_destroyed():
                return
            if running:
                self.editor.is_running_manager.set_running(self, True)
            else:
                self.editor.is_running_manager.set_running(self, False)

    def get_vars(self):
        """
        Get the variables of the running module.
        """
        return main_store.vars()

    T = TypeVar("T")

    def get_store(self, store_type: type[T]) -> T:
        """
        Get a store provided by any extension.
        """
        return main_store.get_store(store_type)

    """
    Node events
    """

    def edge_activated(self, edge: Edge, port: InputPort):
        """
        Called when an edge on an input port is activated.
        """
        pass

    def port_activated(self, port: InputPort):
        """
        Called when an input port is activated, which means either
        1. an connected edge is activated
        2. or the control on the port is activated.
        """
        pass

    def input_edge_added(self, edge: Edge, port: InputPort):
        """
        Called when an edge is added to an input port.
        """
        pass

    def input_edge_removed(self, edge: Edge, port: InputPort):
        """
        Called when an edge is removed from an input port.
        """
        pass

    def output_edge_added(self, edge: Edge, port: OutputPort):
        """
        Called when an edge is added to an output port.
        """
        pass

    def output_edge_removed(self, edge: Edge, port: OutputPort):
        """
        Called when an edge is removed from an output port.
        """
        pass

    def icon_clicked(self):
        """
        Called when the node is double clicked by an user.
        """
        pass
