from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from grapycal_audio import GrapycalAudio

from grapycal import Node


class FilterNode(Node):
    category = "audio/filter"

    def build_node(self):
        self.label_topic.set("Filter")
        self.in_port = self.add_in_port("input", 1)
        self.out_port = self.add_out_port("output")

    def port_activated(self, port):
        if self.in_port.is_all_ready():
            self.run(self.task, background=False)

    def task(self):
        samples = self.in_port.get()
        self.out_port.push(self.filter(samples))

    def filter(self, samples):
        pass


class LowPassFilterNode(FilterNode):
    """ """

    ext: "GrapycalAudio"

    def build_node(self):
        super().build_node()
        self.label_topic.set("Low Pass Filter")

    def init_node(self):
        super().init_node()
        cutoff = 800
        self.a = 2.71828 ** (-6.28318530718 * cutoff / self.ext.sample_rate)
        self.y = 0

    def filter(self, samples):
        y = []
        for x in samples:
            self.y = self.a * self.y + (1 - self.a) * x
            y.append(self.y)
        return y
