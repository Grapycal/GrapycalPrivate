def func():
    """
    A decorator to register a node funcion to the Node.

    Example::

        class AddNode(Node):
            @func()
            def add(self, a: int, b: int) -> int:
                return a + b
    """

    def wrapper(func):
        func._is_node_func = True

        return func

    return wrapper


def param():
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
        func._is_node_param = True

        return func

    return wrapper
