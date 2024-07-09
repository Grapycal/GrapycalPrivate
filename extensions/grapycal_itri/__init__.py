import json
import os

from grapycal import Extension, Node, SourceNode, TextControl
from grapycal.sobjects.controls.sliderControl import SliderControl
from grapycal.sobjects.functionNode import FunctionNode
from grapycal.sobjects.port import InputPort

# from grapycal_torch.moduleNode import SimpleModuleNode
from grapycal_torch.moduleNode import SimpleModuleNode
from grapycal_torch.store import GrapycalTorchStore
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
    dependencies = ["grapycal_torch"]


class QADataset(Dataset):
    """
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
    """

    def __init__(self, path: str):
        self.contexts, self.pair_idx = self.load_data(path)
        self.length = len(self.pair_idx)

    def load_data(self, path: str):
        with open(os.path.join(path), "r") as f:
            contexts = json.load(f)

        # cumulative_length = []
        # for context in contexts:
        #     cumulative_length.append(len(context['qa_pairs']))

        pair_idx = []
        for i, context in enumerate(contexts):
            pair_idx.extend([(i, j) for j in range(len(context["qa_pairs"]))])

        return contexts, pair_idx

    def __getitem__(self, index):
        context_idx, pair_idx = self.pair_idx[index]
        context = self.contexts[context_idx]
        question, answer = context["qa_pairs"][pair_idx]
        return context["context"], question, answer

    def __len__(self):
        return self.length


class QADatasetNode(SourceNode):
    category = "torch/dataset"

    def build_node(self):
        super().build_node()
        self.label_topic.set("QA Dataset")
        self.out_port = self.add_out_port("dataset")
        self.path_port = self.add_in_port("path", control_type=TextControl)

    def task(self):
        dataset = self.load_dataset()
        self.out_port.push(dataset)

    def load_dataset(self):
        return QADataset(path=self.path_port.get())


class SplitCorpusNode(FunctionNode):
    """
    Split each string in the list into multiple string shorter than the specified length.
    """

    category = "torch/text"
    inputs = ["text list"]
    outputs = ["result"]
    max_in_degree = [1]

    def build_node(self):
        super().build_node()
        self.shape_topic.set("normal")
        self.label_topic.set("Split Corpus")
        self.length_port = self.add_in_port(
            "max length", control_type=SliderControl, min=1, max=1000, step=1, value=500
        )

    def calculate(self, text_list: list[str]) -> list[str]:
        max_length = self.length_port.get()
        result = []
        for text in text_list:
            for i in range(0, len(text), max_length):
                result.append(text[i : i + max_length])
        return result


class OpenAINode(Node):
    category = "openai"

    def build_node(self):
        super().build_node()
        self.label_topic.set("OpenAI")
        self.system_message = self.add_in_port(
            "system message",
            control_type=TextControl,
        )
        self.user_message = self.add_in_port(
            "user message",
            control_type=TextControl,
        )
        self.response = self.add_out_port("response")
        self.css_classes.append("fit-content")

    def init_node(self):
        self.openai = None

    def port_activated(self, port: InputPort):
        for port in [self.system_message, self.user_message]:
            if not port.is_all_ready():
                return
        self.run(
            self.task,
            system_message=self.system_message.get(),
            user_message=self.user_message.get(),
        )

    def icon_clicked(self):
        for port in [self.system_message, self.user_message]:
            if not port.is_all_ready():
                return
        self.run(
            self.task,
            system_message=self.system_message.get(),
            user_message=self.user_message.get(),
        )

    def task(self, system_message: str, user_message: str):
        if self.openai is None:
            self.openai = OpenAI()

        response = self.openai.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {"role": "user", "content": user_message},
            ],
            model="gpt-3.5-turbo",
        )
        self.response.push(response.choices[0].message.content)


class GPT2ChineseEncodeNode(FunctionNode):
    category = "torch/nlp"

    inputs = ["text"]
    max_in_degree = [1]
    outputs = ["tokens"]

    def build_node(self):
        super().build_node()
        self.label_topic.set("GPT2 Chinese: Encode")
        self.shape_topic.set("normal")

    def init_node(self):
        super().init_node()
        self.tokenizer = None

    def calculate(self, text):
        if self.tokenizer is None:
            self.tokenizer = BertTokenizer.from_pretrained(
                "uer/gpt2-distil-chinese-cluecorpussmall"
            )
        encoded = self.tokenizer.encode(text)[1:-1]  # remove the [CLS] and [SEP] tokens
        return self.get_store(GrapycalTorchStore).to_tensor(encoded)


class GPT2ChineseDecodeNode(FunctionNode):
    category = "torch/nlp"

    inputs = ["tokens"]
    max_in_degree = [1]
    outputs = ["text"]

    def build_node(self):
        super().build_node()
        self.label_topic.set("GPT2 Chinese: Decode")
        self.shape_topic.set("normal")

    def init_node(self):
        super().init_node()
        self.tokenizer = None

    def calculate(self, tokens):
        if self.tokenizer is None:
            self.tokenizer = BertTokenizer.from_pretrained(
                "uer/gpt2-distil-chinese-cluecorpussmall"
            )
        decoded = self.tokenizer.decode(tokens)
        return decoded.replace(" ", "")


class GPT2ChineseNode(SimpleModuleNode):
    category = "torch/network"

    inputs = ["inp"]
    max_in_degree = [1]
    outputs = ["logits", "loss"]

    def build_node(self):
        super().build_node()
        self.label_topic.set("GPT2 Chinese")

    def create_module(self) -> Module:
        module = GPT2LMHeadModel.from_pretrained(
            "uer/gpt2-distil-chinese-cluecorpussmall"
        )
        assert isinstance(module, Module)
        return module

    def forward(self, inp):
        res = self.module(inp, labels=inp)
        return res.logits, res.loss


class VectorDbMockNode(FunctionNode):
    category = "data"
    inputs = ["query"]
    outputs = ["response"]
    max_in_degree = [1]

    def build_node(self):
        super().build_node()
        self.label_topic.set("Vector DB (mock)")
        self.shape_topic.set("normal")

    def calculate(self, query):
        if "圖書館" in query:
            return "圖書館空調設備因為必須顧慮到保存藏書的品質，所以必須兼顧空氣中的濕度與溫度。一般而言，高溫高濕時會加速纖維氧化分解，也會增加黴菌等微生物的活性而危害紙張，因此溫度20℃、濕度50％為書籍理想保存條件。"
        if "濾網" in query:
            return "許多空調機只有很普通的濾網，過濾灰塵及阻止黴菌滋生效果非常有限，因此灰塵及黴菌會堆積在空調機的風道、熱交換器及風扇上，而多數空調機有許多地方必須由專業人士拆機才能洗到（市面上有許多空調機清洗劑，但這種方法洗不到空調機深處，因此效益有限），若沒有定期由專人清洗（常開啟空調的家庭，清洗間隔可能要低於一年），空調機反而會劣化空氣品質。"
        if "壓縮機" in query:
            return "壓縮機主要有兩種分類方式：第一種分類方式以壓縮機方式分類，可分為容積式 (positive displacement)和動力式(dynamic)兩大類。 容積式壓縮機將輸入功以壓縮機構傳輸，透過改變壓縮室的相對容積，造成冷媒蒸氣容積減少、壓力上升，此類型的壓縮機又可分為往復式、迴轉式、螺旋式和渦捲式；動力式壓縮機利用外力驅動旋轉機構，迫使冷媒蒸氣接收角動量引起分子推擠，從而造成蒸氣相對容積減少，產生壓縮效果，此類壓縮機之代表為離心式壓縮機。圖一所示為以壓縮方式分類之冷媒壓縮機類型。"
        return "空氣調節，簡稱空調，是包含溫度、濕度、空氣清淨度以及空氣循環的控制系統。這與冷氣機／空調供應冷氣、暖氣或除濕的作用原理均類似，大部分利用冷媒在壓縮機的作用下，發生蒸發或凝結，從而引發週遭空氣的蒸發或凝結，以達到改變溫、濕度的目的。冷氣機及暖氣機的效率會用性能係數來表示，是輸入功和提供熱能（或抽出熱能）的比例值，一般來說，直流馬達比交流省電，變頻比傳統壓縮機省電，因為能夠節省大量的電費，直流變頻型態逐漸成為市場主流。"


del SimpleModuleNode, Node, FunctionNode
