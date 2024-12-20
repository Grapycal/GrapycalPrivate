import io
import pprint

from grapycal import TextControl, Node, Edge, InputPort


def get_pprint_str(data):
    output = io.StringIO(newline="")
    if isinstance(data, str):
        output.write(data)
    else:
        pprint.pprint(data, stream=output)
    return output.getvalue()


class PrintNode(Node):
    """
    Display the data received from the input edge.

    :inputs:
        - data: data to be displayed

    """

    category = "interaction"

    def build_node(self):
        self.add_in_port("", max_edges=1)
        self.text_control = self.add_control(TextControl, name="text", readonly=True)
        self.label_topic.set("Print")
        self.shape_topic.set("simple")
        self.css_classes.append("fit-content")

    def edge_activated(self, edge, port):
        self.flash_running_indicator()
        data = edge.get()
        self.text_control.text.set(get_pprint_str(data))

    def input_edge_added(self, edge: Edge, port: InputPort):
        if edge.is_data_ready():
            self.flash_running_indicator()
            data = edge.get()
            self.text_control.text.set(get_pprint_str(data))

    def input_edge_removed(self, edge: Edge, port: InputPort):
        self.text_control.text.set("")
