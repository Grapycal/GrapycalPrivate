import time
from threading import Lock

from grapycal import Node, param, Edge, InputPort, ClockTrait


class LimiterNode(Node):
    category = "procedural"

    def define_traits(self):
        return ClockTrait(self.tick, 0.1)

    def build_node(self):
        super().build_node()
        self.label_topic.set("Limiter")
        self.shape_topic.set("simple")
        self.in_port = self.add_in_port("in", display_name="")
        self.out_port = self.add_out_port("out", display_name="")

    def init_node(self):
        self.value = None
        self.has_value = False
        self.lock = Lock()
        self.counter = 0
        self.last_push_time = 0

    @param()
    def param(self, reduce_factor: int = 10, time_span: float = 0.2):
        self.reduce_factor = reduce_factor
        self.time_span = time_span

    def edge_activated(self, edge: Edge, port: InputPort):
        with self.lock:
            self.value = edge.get()
            self.counter += 1
            self.has_value = True

            if self.reduce_factor == 0:
                return
            if self.counter == self.reduce_factor:
                self.counter = 0
                self.last_push_time = time.time()
                self.has_value = False
                self.out_port.push(self.value)
                self.value = None

    def tick(self):
        if not self.has_value:
            return
        if self.time_span == 0:
            return

        with self.lock:
            if (
                self.value is not None
                and time.time() - self.last_push_time > self.time_span
            ):
                self.counter = 0
                self.last_push_time = time.time()
                self.has_value = False
                self.out_port.push(self.value)
                self.value = None
