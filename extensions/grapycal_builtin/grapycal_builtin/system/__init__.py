import json
import os

import dotenv
from grapycal import InputPort, Node, SourceNode, TextControl


class LoadDotEnvNode(SourceNode):
    '''
    Parse a .env file and then load all the variables found as environment variables.
    '''
    category = 'system'
    def build_node(self):
        super().build_node()
        self.label.set('Load .env')
        self.shape.set('simple')
        self.css_classes.append('fit-content')
        self.out_port = self.add_out_port('run')
        
    def task(self):
        dotenv.load_dotenv("./.env")
        self.out_port.push(None)

class EnvironmentVariableNode(SourceNode):
    '''

    :inputs:
        - run: send in a signal to actively output the environment variable's value
        - set: set the environment variable's value

    :outputs:
        - get: get the environment variable's value

    '''
    category = 'system'
    
    def build_node(self):
        super().build_node()
        self.in_port = self.add_in_port('set',1)
        self.out_port = self.add_out_port('get')
        self.variable_name = self.add_control(TextControl,name='variable_name')
        self.label.set('Environment Variable')
        self.shape.set('simple')
        self.css_classes.append('fit-content')

    def port_activated(self, port: InputPort):
        if port == self.in_port:
            os.environ[self.variable_name.text.get()] = port.get()
        self.flash_running_indicator()

    def task(self):
        if self.variable_name.text.get() not in os.environ:
            self.print_exception(f'Environment Variable "{self.variable_name.text.get()}" does not exist')
            return
        value = os.environ[self.variable_name.text.get()]
        self.out_port.push(value)

class ReadJsonNode(SourceNode):
    '''
    Read a JSON file and output the data.
    '''
    category = 'system'
    def build_node(self):
        super().build_node()
        self.label.set('Read JSON')
        self.css_classes.append('fit-content')
        self.out_port = self.add_out_port('data')
        self.path_port = self.add_in_port('path', control_type=TextControl)
        
    def task(self):
        with open(self.path_port.get(), 'r') as f:
            data = json.load(f)
        self.out_port.push(data)

class WriteJsonNode(Node):
    '''
    Write data to a JSON file.
    '''
    category = 'system'
    def build_node(self):
        super().build_node()
        self.label.set('Write JSON')
        self.css_classes.append('fit-content')
        self.in_port = self.add_in_port('data',1)
        self.path_port = self.add_in_port('path', control_type=TextControl)
        
    def port_activated(self, port: InputPort):
        if port == self.in_port:
            self.run(self.task)
        
    def task(self):
        with open(self.path_port.get(), 'w') as f:
            json.dump(self.in_port.get(), f, ensure_ascii=False)