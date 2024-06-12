import importlib
import inspect
import logging
import os
import sys
from types import ModuleType
from typing import Any, Callable, Dict, List, TypeVar

from objectsync import SObject

from grapycal.extension.utils import get_extension_info, snap_node
from grapycal.sobjects.node import Node
from grapycal.sobjects.port import InputPort, OutputPort
from grapycal.stores import main_store

logger = logging.getLogger(__name__)


def command(name: str):
    def decorator(func: Callable[[Any, CommandCtx], None]):
        func._slash_command_name = name
        return func

    return decorator


class CommandCtx:
    def __init__(self, editor_id: int, mouse_pos: List[float], client_id: int) -> None:
        self.editor_id = editor_id
        self.mouse_pos = mouse_pos
        self.client_id = client_id


class ExtensionMeta(type):
    # find all slash commands
    def __init__(self, name, bases, dct):
        super().__init__(name, bases, dct)
        # self._slash_commands = {}
        # for name, obj in inspect.getmembers(self):
        #     if hasattr(obj, '_slash_command_name'):
        #         self._slash_commands[obj._slash_command_name] = {'name': obj._slash_command_name, 'callback': obj}


class Extension(metaclass=ExtensionMeta):
    dependencies: List[str] = []
    """List of extension names that this extension depends on. When they reload, this extension will also reload.
    #TODO: check dependencies when loading extensions 
    """

    node_types: List[type[Node]] | None = None
    """Specify this list with all the Node types that the extension provides. 

    If unset, the extension will be automatically scanned for all Node types in the module."""

    _slash_commands: Dict[str, dict]

    def __init__(
        self,
        extension_name: str,
        module: ModuleType,
        existing_node_types: set[type[SObject]] = set(),
    ) -> None:
        self.name = extension_name
        self.version = (
            module.__version__
            if hasattr(module, "__version__")
            else get_extension_info(extension_name)["version"]
        )

        self._ctx: CommandCtx | None = None

        self.node_types_d: Dict[str, type[Node]] = {}
        self.node_types_d_without_extension_name: Dict[str, type[Node]] = {}
        if self.node_types is None:
            self.node_types = []
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Node):
                    type_name = f"{self.name}.{obj.__name__}"

                    """
                    It may happen that the same node type is defined in multiple extensions. It is possible caused
                    by diamond-imports. For example, grapycal_ext1 and grapycal_ext2 both import FunctionNode from 
                    grapycal.sobjects.functionNode, and both mistakenly expose it in their __init__.py. This will
                    cause an error when trying to register the node type to ObjectSync. To prevent this, we check
                    if the node type already exists in the existing_node_types dict. If it does, we skip it.
                    Not very elegant, but hope it works.
                    """
                    if obj in existing_node_types:
                        logger.warning(
                            f"Node type {type_name} already exists. Skipping"
                        )
                        continue
                    self.node_types.append(obj)

        for obj in self.node_types:
            type_name = f"{self.name}.{obj.__name__}"
            self.node_types_d[type_name] = obj
            self.node_types_d_without_extension_name[obj.__name__] = obj
            obj.set_extension(self)  # so they can reference the extension

        self.singletonNodeTypes: Dict[str, type[Node]] = {}
        for name, t in self.node_types_d.items():
            if t._is_singleton:
                self.singletonNodeTypes[name] = t

    def add_extension_name_to_node_type(self, node_type: str) -> str:
        return f"{self.name}.{node_type}"

    def get_info(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
        }

    def _wrap(self, callback):
        def wrapper(ctx: CommandCtx):
            self._ctx = ctx
            with main_store.record():
                callback(ctx)
            self._ctx = None

        return wrapper

    def get_slash_commands(self) -> Dict[str, dict]:
        # return self._slash_commands
        slash_commands = {}
        for name, obj in inspect.getmembers(self):
            if hasattr(obj, "_slash_command_name"):
                callback = self._wrap(obj)
                slash_commands[obj._slash_command_name] = {
                    "name": obj._slash_command_name,
                    "callback": callback,
                }
        return slash_commands

    """ some interfaces for the extension to interact with the app"""

    T = TypeVar("T", bound=Node)

    def create_node(
        self,
        node_type: type[T],
        translation: list[float] = [0, 0],
        snap: bool = True,
        **kwargs,
    ) -> T:
        x = translation[0]
        y = translation[1]
        if snap:
            x = snap_node(x)
            y = snap_node(y)
        translation = [x, y]
        node = main_store.main_editor.create_node(
            node_type, translation=translation, **kwargs
        )
        assert isinstance(node, node_type)
        if self._ctx is not None:
            node.add_tag(f"pasted_by_{self._ctx.client_id}")
        return node

    def create_node_with_name(
        self,
        node_type: str,
        translation: list[float] = [0, 0],
        snap: bool = True,
        **kwargs,
    ) -> Node:
        x = translation[0]
        y = translation[1]
        if snap:
            x = snap_node(x)
            y = snap_node(y)
        translation = [x, y]
        node = main_store.main_editor.create_node(
            node_type, translation=translation, **kwargs
        )
        assert isinstance(node, Node)
        if self._ctx is not None:
            node.add_tag(f"pasted_by_{self._ctx.client_id}")
        return node

    def create_edge(self, tail: OutputPort, head: InputPort):
        main_store.main_editor.create_edge(tail, head)

    def register_command(self, name: str, callback: Callable[[CommandCtx], None]):
        main_store.slash.register(name, self._wrap(callback), source=self.name)

    def unregister_command(self, name: str):
        main_store.slash.unregister(name, source=self.name)

    def has_command(self, name: str):
        return main_store.slash.has_command(name, source=self.name)

    def get_data_path(self, path: str) -> str:
        return os.path.join(main_store.settings.data_path.get(), path)

    T = TypeVar("T")

    def get_store(self, store_type: type[T]) -> T:
        return main_store.get_store(store_type)

    def provide_stores(self) -> List[Any]:
        """
        Override this method to return a list of stores that the extension provides.
        A store is any type of object that can be accessed by other extensions. Stores are identified by their type, so please make sure that the type is unique.

        A store will be replaced if the extension that provides it is reloaded.

        Example:
        ```
        class MyExtension(Extension):
            def provide_stores(self):
                return [MyStore()]

        class SomeNode(Node): # this node may be in a different extension
            def init_node(self):
                self.my_store = self.get_store(MyStore) # can access the store like this to exchange data with other nodes
        ```
        """
        return []


def load_or_reload_module(module_name: str):
    if module_name not in sys.modules:
        module = importlib.import_module(module_name)
    else:
        # if the module is obfuscated, we can't reload it. This seems to be a limitation of Pyarmor.
        # Check if the module is obfuscated by checking if it is started with # Pyarmor

        file = sys.modules[module_name].__file__
        if file is not None and open(file).readline().startswith("# Pyarmor"):
            raise ImportError(
                f"Only source code extensions can be reloaded. {module_name} is not. If you want to reload it, please restart the app."
            )

        # delete all decentants of the module from sys.modules.
        # this trick makes importlib.import_module reload the module completely
        # (importlib.reload only reloads the module itself, not its decentants)
        for submodule_name in list(sys.modules.keys()):
            root_name = submodule_name.split(".")[0]
            if root_name == module_name:
                sys.modules.pop(submodule_name)

        module = importlib.import_module(module_name)
    return module


def get_extension(
    extension_name: str, existing_node_types: set[type[SObject]] = set()
) -> "Extension":
    """
    Finds an importable module with the given name and parses it into an Extension object.
    """
    try:
        module = load_or_reload_module(extension_name)
    except ModuleNotFoundError:
        logger.error(
            f"Error loading extension {extension_name}. Make sure it is installed."
        )
        raise

    extension = None

    # find if the user has defined a class that inherits from Extension
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, Extension):
            if obj == Extension:
                continue
            extension = obj(extension_name, module, existing_node_types)
            break

    # if not, just take all the Node classes and put them in the extension
    if extension is None:
        subclass = type(extension_name, (Extension,), {})
        extension = subclass(extension_name, module, existing_node_types)

    return extension
