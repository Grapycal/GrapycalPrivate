from ast import pattern
from typing import Any
from grapycal import FunctionNode, IntTopic, StringTopic
from grapycal.extension.utils import NodeInfo
from grapycal.sobjects.controls.textControl import TextControl
import torch
import einops

class CatNode(FunctionNode):
    category = 'torch/operations'
    def build_node(self):
        self.label.set('🐱0')
        self.shape.set('round')
        self.dim = self.add_attribute('dim',IntTopic,0,editor_type='int')
        self.add_in_port('inputs')
        self.add_out_port('out')
    
    def init_node(self):
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self,dim):
        self.label.set('🐱'+str(dim))
    
    def calculate(self, inputs: list[Any]):
        return torch.cat(inputs,dim=self.dim.get())

class StackNode(FunctionNode):
    category = 'torch/operations'
    def build_node(self):
        self.dim = self.add_attribute('dim',IntTopic,editor_type='int')
        self.label.set('☰0')
        self.shape.set('round')
        self.add_in_port('inputs')
        self.add_out_port('out')
    
    def init_node(self):
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self,dim):
        self.label.set('☰'+str(dim))
    
    def calculate(self, inputs: list[Any]):
        return torch.stack(inputs,dim=self.dim.get())
    
class UnsqueezeNode(FunctionNode):
    category = 'torch/operations'
    def build_node(self):
        self.dim = self.add_attribute('dim',IntTopic,editor_type='int')
        self.label.set('U0')
        self.shape.set('round')
        self.add_in_port('inputs')
        self.add_out_port('out')
    
    def init_node(self):
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self,dim):
        self.label.set('U'+str(dim))
    
    def calculate(self, inputs):
        return torch.unsqueeze(inputs[0],dim=self.dim.get())
    
class SqueezeNode(FunctionNode):
    category = 'torch/operations'
    def build_node(self):
        self.dim = self.add_attribute('dim',IntTopic,editor_type='int')
        self.label.set('S0')
        self.shape.set('round')
        self.add_in_port('inputs')
        self.add_out_port('out')
    
    def init_node(self):
        self.dim.on_set.add_manual(self.dim_changed)
        if self.is_new:
            self.dim.set(0)

    def dim_changed(self,dim):
        self.label.set('S'+str(dim))
    
    def calculate(self, inputs):
        return torch.squeeze(inputs[0],dim=self.dim.get())
    
class RearrangeNode(FunctionNode):
    category = 'torch/operations'
    def build_node(self):
        super().build_node()
        self.pattern_control = self.add_control(TextControl,name='pattern_control',label='')
        self.label.set('Rearrange')
        self.shape.set('simple')
        self.add_in_port('inputs')
        self.add_out_port('out')
        self.css_classes.append('fit-content')

    def init_node(self):
        super().init_node()
        if self.is_new:
            self.pattern_control.text.set('b c h w -> b (c h w)')

    def restore_from_version(self, version: str, old: NodeInfo):
        super().restore_from_version(version, old)
        self.restore_controls('pattern_control')

    def calculate(self, inputs):
        raw_arg = self.pattern_control.text.get().split(',')
        pattern = raw_arg[0]
        axes_lengths = {}
        for arg in raw_arg[1:]:
            key,value = arg.split('=')
            key = key.strip()
            value = int(value.strip())
            axes_lengths[key] = value
            
        return einops.rearrange(inputs[0],pattern,**axes_lengths)
    
class BackwardNode(FunctionNode):
    category = 'torch/operations'
    inputs = ['inputs']
    def build_node(self):
        super().build_node()
        self.label.set('↤')
        self.shape.set('round')

    def calculate(self, inputs: list[Any]):
        inputs[0].backward()

class ToCudaNode(FunctionNode):
    category = 'torch/operations'
    inputs = ['inputs']
    outputs = ['tensor']
    display_port_names = False
    def build_node(self):
        super().build_node()
        self.label.set('cu')
        self.shape.set('round')

    def calculate(self, inputs: list[Any]):
        return inputs[0].cuda()