import re

from grapycal import ButtonControl, Edge, InputPort, ListTopic
from grapycal.sobjects.node import Node


class StepsNode(Node):
    category = 'procedural'

    def build_node(self):
        self.in_port = self.add_in_port('',1)
        self.label.set('Steps')
        self.shape.set('normal')
        self.steps = self.add_attribute('steps', ListTopic, editor_type='list')
        self.add_btn = self.add_control(ButtonControl)
        self.add_btn.label.set('+')
        self.add_btn.on_click.add_auto(self.add_pressed)
        self.css_classes.append('fit-content')
        self.icon_path.set('steps')

        if self.is_new:
            self.steps.insert('1')
            self.add_step('1',-1)
        else:
            for step in self.steps:
                self.add_step(step,-1)

    def init_node(self):
        self.steps.add_validator(ListTopic.unique_validator)
        self.steps.on_insert.add_auto(self.add_step)
        self.steps.on_pop.add_auto(self.remove_step)

    def add_pressed(self):
        new_step = 0
        for step in self.steps:
            if re.match(r'[0-9]+', step):
                new_step = max(new_step, int(step))
        new_step += 1
        self.steps.insert(str(new_step))

    def add_step(self, step, position):
        self.add_out_port(step)

    def remove_step(self, step, position):
        self.remove_out_port(step)

    def edge_activated(self, edge: Edge, port: InputPort):
        self.run(self.task)

    def double_click(self):
        self.run(self.task)

    def task(self):
        self.data = self.in_port.get(allow_no_data=True)
        self.iterator = iter(self.steps.get()) #type: ignore
        self.run(self.next)
        
    def next(self):
        try:
            step = next(self.iterator) #type: ignore
        except StopIteration:
            # release memory
            del self.data
            del self.iterator
            return
        self.run(self.next,to_queue=False)

        port = self.get_out_port(step)
        port.push(self.data)