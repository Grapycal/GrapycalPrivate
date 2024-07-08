import inspect
from typing import Any, Callable

from grapycal.extension_api.node_def import (
    SHOW_ALL_PORTS,
    SHOW_ALL_PORTS_T,
    NodeFuncSpec,
    NodeParamSpec,
)


def func(
    sign_source: Callable | list[Callable | inspect.Parameter] | None = None,
    annotation_override: dict[str, Any] | None = None,
    default_override: dict[str, Any] | None = None,
    shown_ports: list[str] | SHOW_ALL_PORTS_T = SHOW_ALL_PORTS,
    background: bool = True,
):
    """
    A decorator to register a node funcion to the Node.

    Example::

        class AddNode(Node):
            @func()
            def add(self, a: int, b: int) -> int:
                return a + b
    """

    def wrapper(func):
        node_func_spec = NodeFuncSpec(
            func,
            sign_source=sign_source,
            annotation_override=annotation_override,
            default_override=default_override,
            shown_ports=shown_ports,
            background=background,
        )

        func._node_func_spec = node_func_spec

        return func

    return wrapper


def param(
    sign_source: Callable | list[Callable | inspect.Parameter] | None = None,
    annotation_override: dict[str, Any] | None = None,
    default_override: dict[str, Any] | None = None,
    shown_ports: list[str] | SHOW_ALL_PORTS_T = SHOW_ALL_PORTS,
):
    """
    A decorator to register a set of node parameter to the Node.

    Example::

        class ReduceNode(Node):
            @param()
            def param(self, mode: Literal['sum', 'mean']) -> None:
                self.mode = mode

            @func()
            def reduce(self, x: List[int]) -> int:
                if self.mode == 'sum':
                    return sum(x)
                elif self.mode == 'mean':
                    return sum(x) / len(x)
    """

    def wrapper(func):
        node_param_spec = NodeParamSpec(
            func,
            sign_source=sign_source,
            annotation_override=annotation_override,
            default_override=default_override,
            shown_ports=shown_ports,
        )
        func._node_param_spec = node_param_spec
        return func

    return wrapper
