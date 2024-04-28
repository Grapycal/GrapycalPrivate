import json
import os

from grapycal import Extension, Node, SourceNode, TextControl
from grapycal.sobjects.controls.sliderControl import SliderControl
from grapycal.sobjects.functionNode import FunctionNode
from grapycal.sobjects.port import InputPort

# from grapycal_torch.moduleNode import SimpleModuleNode
from grapycal_torch.moduleNode import SimpleModuleNode
from openai import AsyncOpenAI, OpenAI
from torch.nn.modules import Module
from torch.utils.data import Dataset
from transformers import BertTokenizer, GPT2LMHeadModel

# class LMNode(SimpleModuleNode):
#     category = 'torch/neural network'
#     inputs = ['inp']
#     max_in_degree = [1]
#     outputs = ['out']
#     display_port_names = False

class GrapycalItri(Extension):
    dependencies = ['grapycal_torch']

    

class QADataset(Dataset):
    '''
    The dataset on disk should be a folder containing multiple files.
    Each file represents a QA context, it should be a json file with the following format:
    {
        "context": "The context of the QA",
        "qa_pairs": [
            {
                "question": "The question",
                "answer": "The answer"
            },
            ...
        ]
    }
    '''
    def __init__(self, path:str):
        self.contexts, self.pair_idx = self.load_data(path)
        self.length = len(self.pair_idx)

    def load_data(self, path:str):
        with open(os.path.join(path), 'r') as f:
            contexts = json.load(f)
        
        # cumulative_length = []
        # for context in contexts:
        #     cumulative_length.append(len(context['qa_pairs']))

        pair_idx = []
        for i, context in enumerate(contexts):
            pair_idx.extend([(i, j) for j in range(len(context['qa_pairs']))])

        return contexts, pair_idx

    def __getitem__(self, index):
        context_idx, pair_idx = self.pair_idx[index]
        context = self.contexts[context_idx]
        question, answer = context['qa_pairs'][pair_idx]
        return context['context'], question, answer
    
    def __len__(self):
        return self.length
        
class QADatasetNode(SourceNode):
    category = 'torch/dataset'
    def build_node(self):
        super().build_node()
        self.label.set('QA Dataset')
        self.out_port = self.add_out_port('dataset')
        self.path_port = self.add_in_port('path', control_type=TextControl)

    def task(self):
        dataset = self.load_dataset()
        self.out_port.push(dataset)

    def load_dataset(self):
        return QADataset(path=self.path_port.get())
        
class SplitCorpusNode(FunctionNode):
    '''
    Split each string in the list into multiple string shorter than the specified length.
    '''
    category = 'torch/text'
    inputs = ['text list']
    outputs = ['result']
    max_in_degree = [1]

    def build_node(self):
        super().build_node()
        self.shape.set('normal')
        self.label.set('Split Corpus')
        self.length_port = self.add_in_port('max length', control_type=SliderControl, min=1, max=1000, step=1, value=500)
        
    def calculate(self, text_list:list[str]) -> list[str]:
        max_length = self.length_port.get()
        result = []
        for text in text_list:
            for i in range(0, len(text), max_length):
                result.append(text[i:i+max_length])
        return result

class OpenAINode(Node):
    category = 'openai'

    def build_node(self):
        super().build_node()
        self.label.set('OpenAI')
        self.system_message = self.add_in_port('system message', control_type=TextControl, activation_mode = TextControl.ActivationMode.NO_ACTIVATION)
        self.user_message = self.add_in_port('user message', control_type=TextControl, activation_mode = TextControl.ActivationMode.NO_ACTIVATION)
        self.response = self.add_out_port('response')
        self.css_classes.append('fit-content')
        
    def init_node(self):
        self.openai = None

    def port_activated(self, port: InputPort):
        for port in [self.system_message, self.user_message]:
            if not port.is_all_ready():
                return
        self.run(self.task, system_message=self.system_message.get(), user_message=self.user_message.get())

    def double_click(self):
        for port in [self.system_message, self.user_message]:
            if not port.is_all_ready():
                return
        self.run(self.task, system_message=self.system_message.get(), user_message=self.user_message.get())

    def task(self, system_message:str, user_message:str):
        if self.openai is None:
            self.openai = OpenAI()

        response = self.openai.chat.completions.create(
            messages=[
                {
                    'role': 'system',
                    'content': system_message,
                },
                {
                    'role': 'user',
                    'content': user_message
                }
            ],
            model="gpt-3.5-turbo"
        )
        self.response.push(response.choices[0].message.content)

class BertTokenizerEncodeNode(FunctionNode):
    category = 'torch/nlp'

    inputs = ['text']
    max_in_degree = [1]
    outputs = ['tokens']

    def build_node(self):
        super().build_node()
        self.label.set('Bert Tokenizer Encode')
        self.shape.set('normal')

    def init_node(self):
        super().init_node()
        self.tokenizer = None

    def calculate(self, text):
        if self.tokenizer is None:
            self.tokenizer = BertTokenizer.from_pretrained('uer/gpt2-distil-chinese-cluecorpussmall')
        return self.tokenizer.encode(text)
    
class BertTokenizerDecodeNode(FunctionNode):
    category = 'torch/nlp'

    inputs = ['tokens']
    max_in_degree = [1]
    outputs = ['text']

    def build_node(self):
        super().build_node()
        self.label.set('Bert Tokenizer Decode')
        self.shape.set('normal')

    def init_node(self):
        super().init_node()
        self.tokenizer = None

    def calculate(self, tokens):
        if self.tokenizer is None:
            self.tokenizer = BertTokenizer.from_pretrained('uer/gpt2-distil-chinese-cluecorpussmall')
        decoded = self.tokenizer.decode(tokens)
        return decoded.replace(' ', '')
    
class GPT2ChineseNode(SimpleModuleNode):
    category = 'torch/network'

    inputs = ['inp']
    max_in_degree = [1]
    outputs = ['logits','loss']

    def build_node(self):
        super().build_node()
        self.label.set('GPT2 Chinese')

    def create_module(self) -> Module:
        module = GPT2LMHeadModel.from_pretrained("uer/gpt2-distil-chinese-cluecorpussmall")
        assert isinstance(module, Module)
        return module
    
    def generate_label(self)->str:
        return 'GPT2 Chinese'

    def forward(self, inp):
        res = self.module(inp,labels=inp)
        return res.logits, res.loss
    
del SimpleModuleNode, Node, FunctionNode