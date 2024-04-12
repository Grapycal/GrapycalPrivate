import asyncio
from pathlib import Path
from typing import Literal, Sequence, Tuple, Type, cast
from grapycal.extension.utils import NodeInfo
from grapycal_builtin.function.math import AdditionNode
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import InputPort, Port
from grapycal_torch.manager import MNManager, NetManager
from .basic import *
from .cnn import *
from .activation import *
from .tensor_operations import *
from .tensor import *
from .optimizerNode import *
from .transform import *
from .dataloader import *
from .normalize import *
from .loss import *
from .generative import *
from .networkDef import *
from .settings import *
from .configureNode import *
from .pooling import *
from .conversion import *


import torch
torch.set_printoptions(threshold=20)
import torchvision
from torchvision import transforms

from grapycal import GRID, Node, Edge, InputPort, Extension, command, CommandCtx

import io
import matplotlib

matplotlib.use("agg")  # use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

class GrapycalTorch(Extension):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mn = MNManager()
        self.net = NetManager(self)

    @command('Create network: empty')
    def create_network(self,ctx:CommandCtx):
        x = ctx.mouse_pos[0]
        y = ctx.mouse_pos[1]

        name = self.net.next_name('Network')

        in_node = self.create_node(NetworkInNode, [x-150, y], name=name)
        out_node = self.create_node(NetworkOutNode, [x+150, y], name=name)
        tail = in_node.get_out_port('x')
        head = out_node.get_in_port('y')
        self.create_edge(tail, head)

        self.create_node(NetworkCallNode, [x-150, y+100], name=name)

    def create_sequential(self,x:float,y:float,node_types:Sequence[Type[Node]|Tuple[Type[Node],dict]|Literal['\n']],gap:float=2):
        y0 = y
        nodes:List[Node] = []
        for item in node_types:
            if item == '\n':
                x += GRID*12
                y = y0
                continue
            if isinstance(item, tuple):
                nt, kwargs = item
            else:
                nt = item
                kwargs = {}
            new_node = self.create_node(nt, [x, y], **kwargs)
            nodes.append(new_node)
            y += GRID*gap

        for i in range(len(nodes)-1):
            tail = nodes[i].out_ports[0]
            head = nodes[i+1].in_ports[0]
            assert tail is not None and head is not None
            self.create_edge(tail, head)
        
        return nodes, x, y
    
    def wrap_with_network(self,inputs:Dict[str,InputPort],outputs:Dict[str,OutputPort],x1:float,y1:float,x2:float,y2:float,name:str):
        in_node = self.create_node(NetworkInNode, [x1-200, y1-GRID], name=name, inputs=list(inputs.keys()))
        out_node = self.create_node(NetworkOutNode, [x2+150, y2-GRID*3], name=name, outputs=list(outputs.keys()))
        for inp, port in inputs.items():
            tail = in_node.get_out_port(inp)
            assert tail is not None
            self.create_edge(tail, port)

        for outp, port in outputs.items():
            head = out_node.get_in_port(outp)
            assert head is not None
            self.create_edge(port, head)

    def set_num_features(self,nodes:Sequence[Node],num_features:List[int]):
        i = 0
        for node in nodes:
            if isinstance(node,LinearNode):
                node.in_features.set(num_features[i])
                node.out_features.set(num_features[i+1])
                i += 1
            if isinstance(node,Conv2dNode):
                node.in_channels.set(num_features[i])
                node.out_channels.set(num_features[i+1])
                i += 1

    def create_mlp(self,ctx:CommandCtx,node_types:Sequence[Type[Node]],num_features:List[int]):
        name = self.net.next_name('MLP')

        x, y = ctx.mouse_pos
        nodes, x1, y1 = self.create_sequential(x,y,node_types)

        inputs = {'x':cast(InputPort,nodes[0].in_ports[0])}
        outputs = {'y':cast(OutputPort,nodes[-1].out_ports[0])}

        self.wrap_with_network(inputs,outputs,x,y,x1,y1,name)
        self.set_num_features(nodes,num_features)
    
    @command('Create network: Linear')
    def create_linear(self,ctx:CommandCtx):
        node_types = [LinearNode]
        num_features = [1, 10]
        self.create_mlp(ctx,node_types,num_features)

    @command('Create network: MLP 3 layer')
    def create_mlp_3(self,ctx:CommandCtx):
        node_types = [LinearNode,ReLUNode,LinearNode,ReLUNode,LinearNode]
        num_features = [1, 10, 10, 1]
        self.create_mlp(ctx,node_types,num_features)

    @command('Create network: MLP 5 layer')
    def create_mlp_5(self,ctx:CommandCtx):
        node_types = [LinearNode,ReLUNode]*5
        node_types.pop()
        num_features = [1, 10, 10, 10, 10, 1]
        self.create_mlp(ctx,node_types,num_features)

    @command('Create network: LeNet')
    def create_lenet(self,ctx:CommandCtx):
        node_types = [
            (Conv2dNode,{'in_channels':1,'out_channels':6,'kernel_size':5,'padding':0}),
            ReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            (Conv2dNode,{'in_channels':6,'out_channels':16,'kernel_size':5,'padding':0}),
            ReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            FlattenNode,
            '\n',
            (LinearNode,{'in_features':16*5*5,'out_features':120}),
            ReLUNode,
            (LinearNode,{'in_features':120,'out_features':84}),
            ReLUNode,
            (LinearNode,{'in_features':84,'out_features':10})
        ]
        x0, y0 = ctx.mouse_pos
        nodes, x, y = self.create_sequential(ctx.mouse_pos[0],ctx.mouse_pos[1],node_types,gap=3)
        
        inputs = {'x':cast(InputPort,nodes[0].in_ports[0])}
        outputs = {'y':cast(OutputPort,nodes[-1].out_ports[0])}

        self.wrap_with_network(inputs,outputs,x0,y0,x,y,'LeNet')

    @command('Create network: VGG16')
    def create_vgg16(self,ctx:CommandCtx):
        node_types = [
            (Conv2dNode,{'in_channels':3,'out_channels':64,'kernel_size':3,'padding':1}),
            ReLUNode,
            (Conv2dNode,{'in_channels':64,'out_channels':64,'kernel_size':3,'padding':1}),
            ReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            (Conv2dNode,{'in_channels':64,'out_channels':128,'kernel_size':3,'padding':1}),
            ReLUNode,
            (Conv2dNode,{'in_channels':128,'out_channels':128,'kernel_size':3,'padding':1}),
            ReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            (Conv2dNode,{'in_channels':128,'out_channels':256,'kernel_size':3,'padding':1}),
            ReLUNode,
            (Conv2dNode,{'in_channels':256,'out_channels':256,'kernel_size':3,'padding':1}),
            ReLUNode,
            (Conv2dNode,{'in_channels':256,'out_channels':256,'kernel_size':3,'padding':1}),
            ReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            '\n',
            (Conv2dNode,{'in_channels':256,'out_channels':512,'kernel_size':3,'padding':1}),
            ReLUNode,
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            ReLUNode,
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            ReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            ReLUNode,
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            ReLUNode,
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            ReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            '\n',
            FlattenNode,
            (LinearNode,{'in_features':512*7*7,'out_features':4096}),
            ReLUNode,
            (LinearNode,{'in_features':4096,'out_features':4096}),
            ReLUNode,
            (LinearNode,{'in_features':4096,'out_features':1000})
        ]
        x0, y0 = ctx.mouse_pos
        nodes, x, y = self.create_sequential(ctx.mouse_pos[0],ctx.mouse_pos[1],node_types,gap=3)

        inputs = {'image':cast(InputPort,nodes[0].in_ports[0])}
        outputs = {'class pred':cast(OutputPort,nodes[-1].out_ports[0])}

        self.wrap_with_network(inputs,outputs,x0,y0,x,y,'VGG16')

    @command('Create network: VGG16-BN')
    def create_vgg16_bn(self,ctx:CommandCtx):
        node_types = [
            (Conv2dNode,{'in_channels':3,'out_channels':64,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':64}),
            LeakyReLUNode,
            (Conv2dNode,{'in_channels':64,'out_channels':64,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':64}),
            LeakyReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            (Conv2dNode,{'in_channels':64,'out_channels':128,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':128}),
            LeakyReLUNode,
            (Conv2dNode,{'in_channels':128,'out_channels':128,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':128}),
            LeakyReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            (Conv2dNode,{'in_channels':128,'out_channels':256,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':256}),
            LeakyReLUNode,
            (Conv2dNode,{'in_channels':256,'out_channels':256,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':256}),
            LeakyReLUNode,
            (Conv2dNode,{'in_channels':256,'out_channels':256,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':256}),
            LeakyReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            '\n',
            (Conv2dNode,{'in_channels':256,'out_channels':512,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':512}),
            LeakyReLUNode,
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':512}),
            LeakyReLUNode,
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':512}),
            LeakyReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':512}),
            LeakyReLUNode,
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':512}),
            LeakyReLUNode,
            (Conv2dNode,{'in_channels':512,'out_channels':512,'kernel_size':3,'padding':1}),
            (BatchNorm2dNode,{'num_features':512}),
            LeakyReLUNode,
            (MaxPool2dNode,{'kernel_size':2}),
            '\n',
            FlattenNode,
            (LinearNode,{'in_features':512*7*7,'out_features':4096}),
            LeakyReLUNode,
            (LinearNode,{'in_features':4096,'out_features':4096}),
            LeakyReLUNode,
            (LinearNode,{'in_features':4096,'out_features':1000})
        ]
        x0, y0 = ctx.mouse_pos
        nodes, x, y = self.create_sequential(ctx.mouse_pos[0],ctx.mouse_pos[1],node_types,gap=3)

        inputs = {'image':cast(InputPort,nodes[0].in_ports[0])}
        outputs = {'class pred':cast(OutputPort,nodes[-1].out_ports[0])}
        
        self.wrap_with_network(inputs,outputs,x0,y0,x,y,'VGG16-BN')

    @command('Create network: ResNet18')
    def create_resnet_18(self, ctx: CommandCtx):
        """Create a ResNet18 network using basic blocks without pre-built residual blocks,
        and manually perform skip connections with AdditionNode.
        
        Args:
            ctx (CommandCtx): Command context.
        """
        print("Create ResNet18")
        name = self.net.next_name('ResNet18')

        x, y = ctx.mouse_pos
        inputs = {}
        outputs = {}

        # Initial Convolution
        init_conv = self.create_node(Conv2dNode, [x, y], in_channels=3, out_channels=64, kernel_size=7, stride=2, padding=3)
        x += GRID * 12
        bn = self.create_node(BatchNorm2dNode, [x, y], num_features=64)
        x += GRID * 12
        relu = self.create_node(ReLUNode, [x, y])
        x += GRID * 12
        maxpool = self.create_node(MaxPool2dNode, [x, y], kernel_size=3)

        prev_output = maxpool.out_ports[0]
        inputs['image'] = init_conv.in_ports[0]

        # Define helper function for creating a basic block
        def create_basic_block(x, y, in_channels, out_channels, stride=1):
            conv1 = self.create_node(Conv2dNode, [x, y], in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=stride, padding=1)
            x += GRID * 12
            bn1 = self.create_node(BatchNorm2dNode, [x, y], num_features=out_channels)
            x += GRID * 12
            relu1 = self.create_node(ReLUNode, [x, y])
            x += GRID * 12
            conv2 = self.create_node(Conv2dNode, [x, y], in_channels=out_channels, out_channels=out_channels, kernel_size=3, padding=1)
            x += GRID * 12
            bn2 = self.create_node(BatchNorm2dNode, [x, y], num_features=out_channels)

            return conv1, bn1, relu1, conv2, bn2

        # Sequence of layers/blocks for ResNet18
        layer_configs = [(64, 64, 2), (64, 128, 2), (128, 256, 2), (256, 512, 2)]

        for idx, (in_channels, out_channels, stride) in enumerate(layer_configs):
            # Adjust position for next layer
            x = ctx.mouse_pos[0] + (GRID * 15) * (idx + 1)
            y = ctx.mouse_pos[1]

            # Create two basic blocks per layer config
            for block_idx in range(2):
                if block_idx > 0:
                    stride = 1  # Only the first block in each layer may have stride > 1

                block = create_basic_block(x, y, in_channels, out_channels, stride)
                for node in block:
                    self.create_edge(prev_output, node.in_ports[0]) # TODO, the previous output should be also connected to same addition node with the block's output
                    prev_output = node.out_ports[0]
                y += GRID * 20  # Adjust y position for visual clarity in the graph

                # Addition Node for Skip Connection
                if in_channels != out_channels:
                    # If in_channels and out_channels differ, adaptation is needed (e.g., through a Conv2dNode)
                    # This part is simplified for clarity
                    pass
                else:
                    addition_node = self.create_node(AdditionNode, [x, y])
                    # self.create_edge(block[0].in_ports[0], addition_node.in_ports[0])  # TODO: Skip connection start, the previous output should be also connected to same addition node with the block's output
                    self.create_edge(prev_output, addition_node.in_ports[0])  # Block output
                    prev_output = addition_node.out_ports[0]

        # Final layers
        avg_pool = self.create_node(MaxPool2dNode, [x + GRID * 12, y], kernel_size=7)
        self.create_edge(prev_output, avg_pool.in_ports[0])
        prev_output = avg_pool.out_ports[0]

        fc = self.create_node(LinearNode, [x + GRID * 24, y], in_features=512, out_features=1000)
        self.create_edge(prev_output, fc.in_ports[0])
        outputs['class pred'] = fc.out_ports[0]

        # Wrap with network
        self.wrap_with_network(inputs, outputs, ctx.mouse_pos[0], ctx.mouse_pos[1], x, y, name)


class MnistDatasetNode(SourceNode):
    category = "torch/dataset"

    def build_node(self):
        super().build_node()
        self.label.set("MNIST Dataset")
        self.out = self.add_out_port("MNIST Dataset")
        self.include_labels = self.add_option_control(name='include_labels',options=['True','False'], value= 'True',label='Include labels')
        self.size = self.add_slider_control(label="size",min=1,max=60000,int_mode=True,name="size")

    def task(self):
        transform = transforms.Compose(
            [
                transforms.ToTensor(),
            ]
        )

        with self._redirect_output():
            raw_ds = torchvision.datasets.mnist.MNIST(
                root=main_store.settings.data_path.get(),
                download=True,
                transform=transform,
            )

        size = self.size.get_int()
            
        ds = []
        for i in range(size):
            ds.append(raw_ds[i])

        if self.include_labels.get() == 'False':
            ds = [x[0] for x in ds]

        self.out.push(ds)

import aiofiles



class ImageDataset(torch.utils.data.Dataset): # type: ignore
    """
    Loads all images from a directory into memory
    """

    def __init__(self, directory: str, transform=None, max_size=None):
        super().__init__()
        self.directory = directory
        self.transform = transform
        if self.transform is None:
            # to tensor and minus 0.5 and crop to 208*SNAP6
            self.transform = transforms.Compose(
                [
                    transforms.ToTensor(),
                    transforms.Lambda(lambda x: x - 0.5),
                    transforms.Lambda(lambda x: x[:, 5:-5, 1:-1]),
                ]
            )
        self.max_size = max_size
        self.images = asyncio.run(self.load_images())

    async def load_images(self):
        # concurrent loading from disk using aiofiles
        async def load_image(path):
            async with aiofiles.open(path, "rb") as f:
                return plt.imread(io.BytesIO(await f.read()), format="jpg")

        tasks = []
        n = 0
        for path in Path(self.directory).iterdir():
            if path.is_file():
                tasks.append(load_image(path))
                n += 1
                if self.max_size is not None and n >= self.max_size:
                    print("Loaded", n, "images")
                    break
        return await asyncio.gather(*tasks)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img = self.images[idx]
        if self.transform:
            img = self.transform(img)
        return img


class ImageDatasetNode(SourceNode):
    """
    Loads images from a directory
    """

    category = "torch/dataset"

    def build_node(self):
        super().build_node()
        self.label.set("Image Dataset")
        self.out = self.add_out_port("Image Dataset")
        self.dir = self.add_text_control("", "folder", name="folder")
        self.max_size = self.add_text_control("", "max_size", name="max_size")

    def init_node(self):
        super().init_node()
        self.ds = None

    def restore_from_version(self, version: str, old: NodeInfo):
        super().restore_from_version(version, old)
        self.restore_controls("folder", "max_size")

    def task(self):
        if self.ds is None or self.ds.directory != self.dir.get():
            self.ds = ImageDataset(self.dir.get(), max_size=int(self.max_size.get()))

        self.out.push(self.ds)


class EmaNode(Node):
    """
    Exponential moving average
    """

    category = "torch/transform"

    def build_node(self):
        super().build_node()
        self.label.set("EMA")
        self.reset_port = self.add_in_port("reset")
        self.in_port = self.add_in_port("input")
        self.out_port = self.add_out_port("output")
        self.alpha = self.add_attribute("alpha", FloatTopic, 0.9, editor_type="float")

    def init_node(self):
        super().init_node()
        self.ema = None

    def edge_activated(self, edge: Edge, port: InputPort):
        if port == self.reset_port:
            self.ema = None
            return
        if port == self.in_port:
            self.run(self.task, data=edge.get())

    def task(self, data):
        if self.ema is None:
            self.ema = data
        else:
            self.ema = self.alpha.get() * data + (1 - self.alpha.get()) * self.ema
        self.out_port.push(self.ema)


class AverageNode(Node):
    """
    Average
    """

    category = "torch/transform"

    def build_node(self):
        super().build_node()
        self.label.set("Average")
        self.reset_port = self.add_in_port("reset")
        self.in_port = self.add_in_port("input")
        self.out_port = self.add_out_port("output")

    def init_node(self):
        super().init_node()
        self.sum = 0
        self.num = 0

    def edge_activated(self, edge: Edge, port: InputPort):
        if port == self.reset_port:
            self.sum = 0
            self.num = 0
            return
        if port == self.in_port:
            self.run(self.task, data=edge.get())

    def task(self, data):
        self.sum += data
        self.num += 1
        self.out_port.push(self.sum / self.num)


del ModuleNode, SimpleModuleNode, Node, SourceNode, FunctionNode
