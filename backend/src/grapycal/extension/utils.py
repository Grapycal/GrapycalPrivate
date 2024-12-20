import asyncio
import importlib.util
import logging
from pathlib import Path
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, List, TypeVar

import pkg_resources
from objectsync.sobject import SObjectSerialized

if TYPE_CHECKING:
    from grapycal.extension.extension import Extension

logger = logging.getLogger(__name__)

Input = TypeVar("Input")
Output = TypeVar("Output")


class LazyDict(Generic[Input, Output]):
    def __init__(self, gen: Callable[[Input], Output], keys: List[Input]) -> None:
        self.gen = gen
        self._keys = keys

    def __getitem__(self, idx: Input) -> Output:
        return self.gen(idx)

    def __contains__(self, idx: Input) -> bool:
        return idx in self._keys

    def keys(self):
        return self._keys

    def values(self):
        return [self.gen(k) for k in self._keys]


class AttrInfo:
    def __init__(self, name, type_name, value, is_stateful, order_strict):
        self.name = name
        self.type = type_name
        self.value = value
        self.is_stateful = is_stateful
        self.order_strict = order_strict


class SObjectInfo:
    def __init__(self, serialized: SObjectSerialized):
        self.serialized = serialized
        self.attr_info: Dict[str, AttrInfo] = {}
        self.attributes: Dict[str, Any] = {}
        for (
            name,
            type_name,
            value,
            is_stateful,
            order_strict,
        ) in self.serialized.attributes_info:
            self.attr_info[name] = AttrInfo(
                name, type_name, value, is_stateful, order_strict
            )
            self.attributes[name] = value

    def has_attribute(self, name):
        return name in self.attr_info

    def __getitem__(self, name: str):
        """
        Returns the value of an attribute
        """
        return self.attributes[name]


class ControlInfo(SObjectInfo):
    pass


class PortInfo(SObjectInfo):
    def __init__(self, serialized: SObjectSerialized):
        super().__init__(serialized)
        self.name = self.attributes["name"]


def search_sobjectinfo_by_id(
    serialized: SObjectSerialized, id: str
) -> SObjectSerialized | None:
    """
    Search for an SObjectInfo by id recursively
    """
    if serialized.id == id:
        return serialized
    for child in serialized.children.values():
        child_info = search_sobjectinfo_by_id(child, id)
        if child_info is not None:
            return child_info
    return None


def search_sobjectinfo_by_id_raise(
    serialized: SObjectSerialized, id: str
) -> SObjectSerialized:
    """
    Search for an SObjectInfo by id recursively. Raise an error if not found
    """
    info = search_sobjectinfo_by_id(serialized, id)
    if info is None:
        raise ValueError(f"Cannot find SObjectInfo with id {id}")
    return info


class NodeInfo(SObjectInfo):
    """
    An easier-to-use interface to read SObjectSerialized of a node
    """

    def __init__(self, serialized: SObjectSerialized):
        super().__init__(serialized)
        controls: Dict[str, str] = self.attributes["controls"]
        self.controls_id_to_name = {v: k for k, v in controls.items()}

        def get_controlinfo(name: str) -> ControlInfo:
            # The control can be direct child of the node, or a child of a input port
            control_id = controls[name]
            return ControlInfo(search_sobjectinfo_by_id_raise(serialized, control_id))

        self.controls = LazyDict[str, ControlInfo](
            get_controlinfo, list(controls.keys())
        )

        self.in_ports: Dict[str, PortInfo] = {}
        for id in self.attributes["in_ports"]:
            sin = search_sobjectinfo_by_id_raise(serialized, id)
            port_info = PortInfo(sin)
            self.in_ports[port_info.name] = port_info

        self.out_ports: Dict[str, PortInfo] = {}
        for id in self.attributes["out_ports"]:
            sin = search_sobjectinfo_by_id_raise(serialized, id)
            port_info = PortInfo(sin)
            self.out_ports[port_info.name] = port_info


class Clock:
    def __init__(self, resolution: float):
        self.resolution = resolution
        self.listeners: list[list] = []  # callback, interval, next_time, pass_time
        self.to_add: dict[Callable, Any] = {}
        self.to_remove: set[Callable] = set()

    async def run(self):
        while True:
            for callback in self.to_remove:
                self.listeners = [l for l in self.listeners if l[0] != callback]
            self.to_remove = set()

            for to_add in self.to_add.values():
                self.listeners.append(to_add)
            self.to_add = {}

            current_time = time.time()
            await asyncio.sleep(self.resolution)
            for listener in self.listeners:
                callback, interval, next_time, pass_time = listener
                if current_time >= next_time:
                    if pass_time:
                        callback(current_time)
                    else:
                        callback()
                    next_time = max(
                        next_time + interval, current_time
                    )  # if the callback takes too long, skip the next tick
                    listener[2] = next_time

    def add_listener(
        self,
        callback: Callable[[], None] | Callable[[float], None],
        interval: float,
        pass_time=False,
    ):
        # have to avoid race condition
        self.to_add[callback] = [callback, interval, time.time() + interval, pass_time]

    def remove_listener(self, callback: Callable):
        self.to_remove.add(callback)


def get_package_version(package_name: str) -> str:
    """
    Find the version of a package. Considering editable installs, the developer may have changed the version but not installed it.
    In this case, the new version will not be reflected in pkg_resources. So we first try to find the version in pyproject.toml.
    """

    version = get_package_version_from_pyproject(package_name)
    if version is not None:
        return version

    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        # the package is not installed
        return "0.0.0"


def get_package_version_from_pyproject(package_name: str) -> str | None:
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        return None
    init_location = spec.origin
    if init_location is None:
        return None
    package_location = Path(init_location).parent
    pyproject = Path(package_location) / "pyproject.toml"

    if not pyproject.exists():
        return None

    with open(pyproject, "r") as f:
        pyproject_toml = f.read()

    import toml

    pyproject_toml = toml.loads(pyproject_toml)
    # try poetry
    try:
        return pyproject_toml["tool"]["poetry"]["version"]
    except KeyError:
        pass
    # try pep 621
    try:
        return pyproject_toml["project"]["version"]
    except KeyError:
        pass
    logger.warning(
        f"Package {package_name} has a pyproject.toml but no version is found in it"
    )
    return None


def list_to_dict(list: List[dict], key: str) -> Dict[Any, dict]:
    """
    Convert a list of dicts to a dict of dicts
    """
    return {d[key]: d for d in list}


def get_extension_info(name) -> dict:
    # returns the same as Extension.get_info(), but no need to load the extension
    return {
        "name": name,
        "version": get_package_version(name),
    }


def snap_node(value: float, grid_size: float = 17) -> float:
    return round(value / grid_size) * grid_size


def get_all_dependents(
    target: "Extension", extensions: List["Extension"], include_target: bool = True
) -> List["Extension"]:
    """
    Returns all extensions that depend on the target and the target itself. The order is from the target to the dependents
    """
    res_q = [target]
    search_q = [target]
    while search_q:
        dependency = search_q.pop()
        for e in extensions:
            if dependency.name in e.dependencies:
                if e in res_q:
                    raise ValueError(
                        f"Extension {e.name} has circular dependency with {dependency.name}"
                    )
                res_q.append(e)
                search_q.append(e)

    if not include_target:
        res_q.remove(target)
    return res_q
