from grapycal import FunctionNode
import motor.motor_asyncio as motor

class MongoClientNode(FunctionNode):
    category = 'MongoDB'
    inputs = ['uri']
    max_in_degree = [1]
    outputs = ['client']

    def build_node(self):
        super().build_node()
        self.label.set('MongoClient')
        self.shape.set('normal')
    
    async def calculate(self, **inputs):
        uri = inputs['uri']
        client = motor.AsyncIOMotorClient(uri)
        return client

class MongoCollectionNode(FunctionNode):
    category = 'MongoDB'
    inputs = ['client', 'db_name', 'coll_name']
    max_in_degree = [1, 1, 1]
    outputs = ['coll']

    def build_node(self):
        super().build_node()
        self.label.set('MongoCollection')
        self.shape.set('normal')

    async def calculate(self, **inputs):
        client = inputs['client']
        db_name = inputs['db_name']
        coll_name = inputs['coll_name']
        coll = client[db_name][coll_name]
        return coll

class MongoFindNode(FunctionNode):
    def build_node(self):
        super().build_node()
        self.label.set('MongoFind')
        self.shape.set('normal')
        self.type = self.add_option_control('list', ['list', 'AsyncIOMotorCursor'], 'Type')

    category = 'MongoDB'
    inputs = ['coll', 'filter']
    max_in_degree = [1, 1]
    outputs = ['result']

    async def calculate(self, **inputs):
        coll:motor.AsyncIOMotorCollection = inputs['coll']
        filter:dict = inputs['filter']
        if self.type.get() == 'list':
            result = await coll.find(filter).to_list(None)
        else:
            result = coll.find(filter)
        return result

class MongoFindOneNode(FunctionNode):
    def build_node(self):
        super().build_node()
        self.label.set('MongoFindOne')
        self.shape.set('normal')
        self.type = self.add_option_control('dict', ['dict', 'AsyncIOMotorCursor'], 'Type')
    
    category = 'MongoDB'
    inputs = ['coll', 'filter']
    max_in_degree = [1, 1]
    outputs = ['result']

    async def calculate(self, **inputs):
        coll:motor.AsyncIOMotorCollection = inputs['coll']
        filter:dict = inputs['filter']
        if self.type.get() == 'dict':
            result = await coll.find_one(filter)
        else:
            result = await coll.find_one(filter)
        return result
    
class MongoInsertOneNode(FunctionNode):
    def build_node(self):
        super().build_node()
        self.label.set('MongoInsertOne')
        self.shape.set('normal')

    category = 'MongoDB'
    inputs = ['coll', 'document']
    max_in_degree = [1, 1]
    outputs = ['result']

    async def calculate(self, **inputs):
        coll:motor.AsyncIOMotorCollection = inputs['coll']
        document = inputs['document']
        result = await coll.insert_one(document)
        return result
    
class MongoInsertManyNode(FunctionNode):
    def build_node(self):
        super().build_node()
        self.label.set('MongoInsertMany')
        self.shape.set('normal')

    category = 'MongoDB'
    inputs = ['coll', 'documents']
    max_in_degree = [1, 1]
    outputs = ['result']

    async def calculate(self, **inputs):
        coll:motor.AsyncIOMotorCollection = inputs['coll']
        documents:list[dict] = inputs['documents']
        result = await coll.insert_many(documents)
        return result

class MongoUpdateOneNode(FunctionNode):
    def build_node(self):
        super().build_node()
        self.label.set('MongoUpdateOne')
        self.shape.set('normal')

    category = 'MongoDB'
    inputs = ['coll', 'filter', 'update']
    max_in_degree = [1, 1, 1]
    outputs = ['result']

    async def calculate(self, **inputs):
        coll:motor.AsyncIOMotorCollection = inputs['coll']
        filter:dict = inputs['filter']
        update = inputs['update']
        result = await coll.update_one(filter, update)
        return result
    
class MongoUpdateManyNode(FunctionNode):
    def build_node(self):
        super().build_node()
        self.label.set('MongoUpdateMany')
        self.shape.set('normal')

    category = 'MongoDB'
    inputs = ['coll', 'filter', 'update']
    max_in_degree = [1, 1, 1]
    outputs = ['result']

    async def calculate(self, **inputs):
        coll:motor.AsyncIOMotorCollection = inputs['coll']
        filter:dict = inputs['filter']
        update = inputs['update']
        result = await coll.update_many(filter, update)
        return result
    
class MongoDeleteOneNode(FunctionNode):
    def build_node(self):
        super().build_node()
        self.label.set('MongoDeleteOne')
        self.shape.set('normal')

    category = 'MongoDB'
    inputs = ['coll', 'filter']
    max_in_degree = [1, 1]
    outputs = ['result']

    async def calculate(self, **inputs):
        coll:motor.AsyncIOMotorCollection = inputs['coll']
        filter:dict = inputs['filter']
        result = await coll.delete_one(filter)
        return result

class MongoDeleteManyNode(FunctionNode):
    def build_node(self):
        super().build_node()
        self.label.set('MongoDeleteMany')
        self.shape.set('normal')

    category = 'MongoDB'
    inputs = ['coll', 'filter']
    max_in_degree = [1, 1]
    outputs = ['result']

    async def calculate(self, **inputs):
        coll:motor.AsyncIOMotorCollection = inputs['coll']
        filter:dict = inputs['filter']
        result = await coll.delete_many(filter)
        return result