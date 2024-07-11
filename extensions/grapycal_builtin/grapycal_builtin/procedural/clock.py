from grapycal import SliderControl, InputPort, main_store, Node


class ClockNode(Node):
    """
    Ticks at the rate of at most `rate` Hz.
    """

    def build_node(self):
        self.rate_port = self.add_in_port(
            "rate",
            control_type=SliderControl,
            min=0.01,
            max=10,
            value=1,
            activate_on_control_change=True,
        )
        self.tick_port = self.add_out_port("tick")

    def init_node(self):
        main_store.clock.add_listener(self.tick, 1.0 / self.rate_port.get())

    def port_activated(self, port: InputPort):
        if port == self.rate_port:
            main_store.clock.remove_listener(self.tick)
            main_store.clock.add_listener(self.tick, 1.0 / self.rate_port.get())

    def destroy(self):
        main_store.clock.remove_listener(self.tick)
        return super().destroy()

    def tick(self):
        self.tick_port.push(None)
