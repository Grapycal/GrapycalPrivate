from grapycal import Node, Edge, InputPort


class ListAccumulatorNode(Node):
    category = "data"

    def build_node(self):
        self.label_topic.set("List Accum (0)")
        self.trigger_port = self.add_in_port("trigger")
        self.reset_port = self.add_in_port("reset")
        self.append_port = self.add_in_port("append")
        self.get_port = self.add_out_port("get")

    def init_node(self):
        self.data = []

    def edge_activated(self, edge: Edge, port: InputPort):
        if port == self.trigger_port:
            edge.get()
            self.get_port.push(self.data)
        elif port == self.reset_port:
            edge.get()
            self.data = []
            self.label_topic.set("List Accum (0)")
        elif port == self.append_port:
            self.data.append(edge.get())
            self.label_topic.set(f"List Accum ({len(self.data)})")
