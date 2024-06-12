import io
from grapycal.extension.utils import NodeInfo
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import InputPort
from grapycal.sobjects.sourceNode import SourceNode
from grapycal import ListTopic

import ast

from objectsync import StringTopic
from topicsync.topic import GenericTopic


def separate_last_expr(code) -> tuple[ast.Module, ast.Expr | None]:
    stmts = list(ast.iter_child_nodes(ast.parse(code)))
    if stmts == []:
        return ast.parse(""), None
    if isinstance(stmts[-1], ast.Expr):
        if len(stmts) > 1:
            ast_module = ast.parse("")
            ast_module.body = stmts[:-1]
            return ast_module, stmts[-1]
        return ast.parse(""), stmts[-1]
    else:
        return ast.parse(code), None


# exec that prints correctly
def exec_(code, globals=None, locals=None, print_=None):
    # Separate the last expression from the rest of the code
    rest, last_expr = separate_last_expr(code)
    # Execute the rest of the code
    if rest.body:
        exec(compile(rest, filename="<ast>", mode="exec"), globals, locals)
    # Evaluate the last expression
    if last_expr is not None:
        last = eval(
            compile(
                ast.Expression(body=last_expr.value), filename="<ast>", mode="eval"
            ),
            globals,
            locals,
        )
        if last is not None and print_ is not None:
            print_(last)
        return last


async def aexec(code, globals_=None, locals_=None, print_=None):
    # Separate the last expression from the rest of the code
    rest, last_expr = separate_last_expr(code)

    """
    create an ast that wrap rest and last_expr in an async function (add retyrn last_expr at the end of the function)
    async def __ex():
        rest
        return last_expr
    """
    if last_expr is not None:
        rest.body.append(ast.Return(value=last_expr.value))

    # Wrap the code in an async function
    wrapped_code = ast.Module(
        body=[
            ast.AsyncFunctionDef(
                name="__ex",
                args=ast.arguments(
                    args=[],
                    posonlyargs=[],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[],
                ),
                body=rest.body,
                decorator_list=[],
                returns=None,
            )
        ],
        type_ignores=[],
    )
    wrapped_code = ast.fix_missing_locations(wrapped_code)

    # Execute the wrapped code to get the function
    if locals_ is None:
        locals_ = {}
    exec(compile(wrapped_code, filename="<ast>", mode="exec"), globals_, locals_)
    func = locals_["__ex"]

    # Execute the function
    result = await func()
    if print_ is not None:
        print_(result)

    return result


class ExecNode(SourceNode):
    """
    Equivalent to Python's `exec` function. It executes the statements in the input text box.

    To make it run, either send in a signal to the `run` input port, or double click on the node.

    :inputs:
        - run: send in a signal to run the statements
        - *inputs: You can add any variable of inputs to the node and
                    Click the (+) in the inspector to plus the name of the variable.

    :outputs:
        - done: send out a signal when the statements are done
        - *outputs: You can add any variable of outputs to the node.
                    Click the (+) in the inspector to plus the name of the variable.
    """

    category = "interaction"

    def build_node(self, text=""):
        super().build_node()
        self.out_port = self.add_out_port("done")
        self.code_control = self.add_code_control(name="text")
        self.label.set("Execute")
        self.shape.set("simple")
        self.css_classes.append("fit-content")
        self.output_control = self.add_text_control(
            "", readonly=True, name="output_control"
        )
        self.is_async = self.add_attribute(
            "async", GenericTopic[bool], False, editor_type="toggle"
        )
        self.inputs = self.add_attribute("inputs", ListTopic, [], editor_type="list")
        self.outputs = self.add_attribute("outputs", ListTopic, [], editor_type="list")
        self.print_last_expr = self.add_attribute(
            "print last expr",
            StringTopic,
            editor_type="options",
            options=["yes", "no"],
            init_value="yes",
        )
        self.icon_path_topic.set("python")

        if self.is_new:
            self.code_control.set(text)
        else:
            for name in self.inputs:
                self.add_input(name, None)
            for name in self.outputs:
                self.add_output(name, None)

    def init_node(self):
        super().init_node()
        self.inputs.on_insert.add_auto(self.add_input)
        self.inputs.on_pop.add_auto(self.pop_input)
        self.outputs.on_insert.add_auto(self.add_output)
        self.outputs.on_pop.add_auto(self.pop_output)
        self.code_control.on_execute += lambda: self.run(self.task)
        self.is_async.on_set += lambda v: self.label.set(
            "Execute" + (" (async)" if v else "")
        )

    def add_input(self, name, _):
        self.add_in_port(name, 1)

    def pop_input(self, name, _):
        self.remove_in_port(name)

    def add_output(self, name, _):
        self.add_out_port(name)

    def pop_output(self, name, _):
        self.remove_out_port(name)

    def restore_from_version(self, version: str, old: NodeInfo):
        super().restore_from_version(version, old)
        self.restore_controls("text", "output_control")
        self.restore_attributes("inputs", "outputs")

    def edge_activated(self, edge: Edge, port: InputPort):
        super().edge_activated(edge, port)
        if port == self.run_port:
            return
        for name in self.inputs:
            port = self.get_in_port(name)
            if not port.is_all_ready():
                return
        self.task()

    def task(self):
        if self.is_async.get():
            self.run(self.async_task, background=False)
        else:
            self.run(self.sync_task)

    async def async_task(self):
        self.output_control.set("")
        stmt = self.code_control.text.get()
        for name in self.inputs:
            port = self.get_in_port(name)
            if port.is_all_ready():
                self.get_vars().update({name: port.get()})
        self.get_vars().update(
            {
                "print": self.print,
                "self": self,
            }
        )
        try:
            result = await aexec(stmt, self.get_vars(), print_=self.print)
        except Exception as e:
            self.print_exception(e, -3)
            return
        self.out_port.push(result)
        for name in self.outputs:
            self.get_out_port(name).push(self.get_vars()[name])

    def has_await(self, code: str):
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Await):
                return True
        return False

    def sync_task(self):
        self.output_control.set("")
        stmt = self.code_control.text.get()
        for name in self.inputs:
            port = self.get_in_port(name)
            if port.is_all_ready():
                self.get_vars().update({name: port.get()})
        self.get_vars().update(
            {
                "print": self.print,
                "self": self,
            }
        )
        try:
            result = exec_(
                stmt,
                self.get_vars(),
                print_=self.print if self.print_last_expr.get() == "yes" else None,
            )
        except Exception as e:
            if self.has_await(stmt):
                self.print_exception(
                    f"Failed to run: {e}\n The code seems to be async. Please enable the async toggle of the ExecNode to run async code."
                )
                return
            self.print_exception(e, -3)
            return
        self.out_port.push(result)
        for name in self.outputs:
            self.get_out_port(name).push(self.get_vars()[name])

    def print(self, *args, **kwargs):
        output = io.StringIO()
        print(*args, file=output, **kwargs)
        contents = output.getvalue()
        output.close()
        self.output_control.set(self.output_control.get() + contents)
