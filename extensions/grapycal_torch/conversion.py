from grapycal import Node, StringTopic
from grapycal.sobjects.port import InputPort
import torch
import numpy as np


class ConvertToNode(Node):
    category = 'torch'
    def build_node(self):
        self.in_port = self.add_in_port('input', 1)
        self.out_port = self.add_out_port('output')
        self.css_classes.append('fit-content')
        self.label.set('Convert To')
        self.shape.set('simple')
        self.target = self.add_option_control(name='target', options=['torch tensor', 'numpy array'], value='torch tensor')

    def port_activated(self, port: InputPort):
        self.run(self.task, background=False)

    def task(self):
        data = self.in_port.get()
        if self.target.get() == 'torch tensor':
            self.out_port.push(torch.tensor(data))
        elif self.target.get() == 'numpy array':
            self.out_port.push(np.array(data))