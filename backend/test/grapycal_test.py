from grapycal import Node,IntTopic
from objectsync import StringTopic

class Test1Node(Node):
    category = 'test'
    def build_node(self):
        self.add_in_port('in')
        self.add_out_port('out')
        self.int_topic = self.add_attribute('some_int_topic',IntTopic)
        self.string_topic = self.add_attribute('some_string_topic',StringTopic)
        