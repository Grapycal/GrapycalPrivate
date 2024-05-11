from grapycal import Node
from grapycal.sobjects.port import InputPort

class MongoClientNode(Node):
    category = 'MongoDB'

    def build_node(self):
        super().build_node()
        self.label.set('MongoClient')
        self.connection_string = self.add_in_port('connection_string')
        self.out = self.add_out_port('client')

    def port_activated(self, port: InputPort):
        self.run(self.connect, con_string = port.get())
        
    async def connect(self, con_string:str):
        import motor.motor_asyncio as motor
        self.client = motor.AsyncIOMotorClient(con_string)
        self.out.push(self.client)