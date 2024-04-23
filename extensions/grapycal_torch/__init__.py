import asyncio
import io
from pathlib import Path
from typing import Literal, Sequence, Tuple, Type, cast

import matplotlib
import torch
from grapycal import GRID, CommandCtx, Edge, Extension, InputPort, Node, command
from grapycal.extension.utils import NodeInfo
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import InputPort, Port
from torchvision import transforms

from grapycal_torch.manager import MNManager, NetManager

from .activation import *
from .basic import *
from .cnn import *
from .configureNode import *
from .conversion import *
from .dataloader import *
from .dataset import *
from .generative import *
from .loss import *
from .metrics import *
from .networkDef import *
from .normalize import *
from .optimizerNode import *
from .pooling import *
from .resnet import ResNet
from .settings import *
from .tensor import *
from .tensor_operations import *
from .transform import *

matplotlib.use("agg")  # use non-interactive backend
import aiofiles
import aiohttp
import matplotlib.pyplot as plt
import numpy as np


class GrapycalTorch(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mn = MNManager()
        self.net = NetManager(self)

    @command("Create network: empty")
    def create_network(self, ctx: CommandCtx):
        x = ctx.mouse_pos[0]
        y = ctx.mouse_pos[1]

        name = self.net.next_name("Network")

        in_node = self.create_node(NetworkInNode, [x - 150, y], name=name)
        out_node = self.create_node(NetworkOutNode, [x + 150, y], name=name)
        tail = in_node.get_out_port("x")
        head = out_node.get_in_port("y")
        self.create_edge(tail, head)

        self.create_node(NetworkCallNode, [x - 150, y + 100], name=name)

    def create_sequential(
        self,
        x: float,
        y: float,
        node_types: Sequence[Type[Node] | Tuple[Type[Node], dict] | Literal["\n"]],
        gap: float = 2,
    ):
        y0 = y
        nodes: List[Node] = []
        for item in node_types:
            if item == "\n":
                x += GRID * 12
                y = y0
                continue
            if isinstance(item, tuple):
                nt, kwargs = item
            else:
                nt = item
                kwargs = {}
            new_node = self.create_node(nt, [x, y], **kwargs)
            nodes.append(new_node)
            y += GRID * gap

        for i in range(len(nodes) - 1):
            tail = nodes[i].out_ports[0]
            head = nodes[i + 1].in_ports[0]
            assert tail is not None and head is not None
            self.create_edge(tail, head)

        return nodes, x, y

    def wrap_with_network(
        self,
        inputs: Dict[str, InputPort],
        outputs: Dict[str, OutputPort],
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        name: str,
    ):
        in_node = self.create_node(
            NetworkInNode, [x1 - 200, y1 - GRID], name=name, inputs=list(inputs.keys())
        )
        out_node = self.create_node(
            NetworkOutNode,
            [x2 + 150, y2 - GRID * 3],
            name=name,
            outputs=list(outputs.keys()),
        )
        for inp, port in inputs.items():
            tail = in_node.get_out_port(inp)
            assert tail is not None
            self.create_edge(tail, port)

        for outp, port in outputs.items():
            head = out_node.get_in_port(outp)
            assert head is not None
            self.create_edge(port, head)

    def set_num_features(self, nodes: Sequence[Node], num_features: List[int]):
        i = 0
        for node in nodes:
            if isinstance(node, LinearNode):
                node.in_features.set(num_features[i])
                node.out_features.set(num_features[i + 1])
                i += 1
            if isinstance(node, Conv2dNode):
                node.in_channels.set(num_features[i])
                node.out_channels.set(num_features[i + 1])
                i += 1

    def create_mlp(
        self, ctx: CommandCtx, node_types: Sequence[Type[Node]], num_features: List[int]
    ):
        name = self.net.next_name("MLP")

        x, y = ctx.mouse_pos
        nodes, x1, y1 = self.create_sequential(x, y, node_types)

        inputs = {"x": cast(InputPort, nodes[0].in_ports[0])}
        outputs = {"y": cast(OutputPort, nodes[-1].out_ports[0])}

        self.wrap_with_network(inputs, outputs, x, y, x1, y1, name)
        self.set_num_features(nodes, num_features)

    @command("Create network: Linear")
    def create_linear(self, ctx: CommandCtx):
        node_types = [LinearNode]
        num_features = [1, 10]
        self.create_mlp(ctx, node_types, num_features)

    @command("Create network: MLP 3 layer")
    def create_mlp_3(self, ctx: CommandCtx):
        node_types = [LinearNode, ReLUNode, LinearNode, ReLUNode, LinearNode]
        num_features = [1, 10, 10, 1]
        self.create_mlp(ctx, node_types, num_features)

    @command("Create network: MLP 5 layer")
    def create_mlp_5(self, ctx: CommandCtx):
        node_types = [LinearNode, ReLUNode] * 5
        node_types.pop()
        num_features = [1, 10, 10, 10, 10, 1]
        self.create_mlp(ctx, node_types, num_features)

    @command("Create network: LeNet")
    def create_lenet(self, ctx: CommandCtx):
        node_types = [
            (
                Conv2dNode,
                {"in_channels": 1, "out_channels": 6, "kernel_size": 5, "padding": 0},
            ),
            ReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            (
                Conv2dNode,
                {"in_channels": 6, "out_channels": 16, "kernel_size": 5, "padding": 0},
            ),
            ReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            FlattenNode,
            "\n",
            (LinearNode, {"in_features": 16 * 5 * 5, "out_features": 120}),
            ReLUNode,
            (LinearNode, {"in_features": 120, "out_features": 84}),
            ReLUNode,
            (LinearNode, {"in_features": 84, "out_features": 10}),
        ]
        x0, y0 = ctx.mouse_pos
        nodes, x, y = self.create_sequential(
            ctx.mouse_pos[0], ctx.mouse_pos[1], node_types, gap=3
        )

        inputs = {"x": cast(InputPort, nodes[0].in_ports[0])}
        outputs = {"y": cast(OutputPort, nodes[-1].out_ports[0])}

        self.wrap_with_network(inputs, outputs, x0, y0, x, y, "LeNet")

    @command("Create network: VGG16")
    def create_vgg16(self, ctx: CommandCtx):
        node_types = [
            (
                Conv2dNode,
                {"in_channels": 3, "out_channels": 64, "kernel_size": 3, "padding": 1},
            ),
            ReLUNode,
            (
                Conv2dNode,
                {"in_channels": 64, "out_channels": 64, "kernel_size": 3, "padding": 1},
            ),
            ReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            (
                Conv2dNode,
                {
                    "in_channels": 64,
                    "out_channels": 128,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 128,
                    "out_channels": 128,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            (
                Conv2dNode,
                {
                    "in_channels": 128,
                    "out_channels": 256,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 256,
                    "out_channels": 256,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 256,
                    "out_channels": 256,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            "\n",
            (
                Conv2dNode,
                {
                    "in_channels": 256,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            ReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            "\n",
            FlattenNode,
            (LinearNode, {"in_features": 512 * 7 * 7, "out_features": 4096}),
            ReLUNode,
            (LinearNode, {"in_features": 4096, "out_features": 4096}),
            ReLUNode,
            (LinearNode, {"in_features": 4096, "out_features": 1000}),
        ]
        x0, y0 = ctx.mouse_pos
        nodes, x, y = self.create_sequential(
            ctx.mouse_pos[0], ctx.mouse_pos[1], node_types, gap=3
        )

        inputs = {"image": cast(InputPort, nodes[0].in_ports[0])}
        outputs = {"class pred": cast(OutputPort, nodes[-1].out_ports[0])}

        self.wrap_with_network(inputs, outputs, x0, y0, x, y, "VGG16")

    @command("Create network: VGG16-BN")
    def create_vgg16_bn(self, ctx: CommandCtx):
        node_types = [
            (
                Conv2dNode,
                {"in_channels": 3, "out_channels": 64, "kernel_size": 3, "padding": 1},
            ),
            (BatchNorm2dNode, {"num_features": 64}),
            LeakyReLUNode,
            (
                Conv2dNode,
                {"in_channels": 64, "out_channels": 64, "kernel_size": 3, "padding": 1},
            ),
            (BatchNorm2dNode, {"num_features": 64}),
            LeakyReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            (
                Conv2dNode,
                {
                    "in_channels": 64,
                    "out_channels": 128,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 128}),
            LeakyReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 128,
                    "out_channels": 128,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 128}),
            LeakyReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            (
                Conv2dNode,
                {
                    "in_channels": 128,
                    "out_channels": 256,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 256}),
            LeakyReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 256,
                    "out_channels": 256,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 256}),
            LeakyReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 256,
                    "out_channels": 256,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 256}),
            LeakyReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            "\n",
            (
                Conv2dNode,
                {
                    "in_channels": 256,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 512}),
            LeakyReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 512}),
            LeakyReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 512}),
            LeakyReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 512}),
            LeakyReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 512}),
            LeakyReLUNode,
            (
                Conv2dNode,
                {
                    "in_channels": 512,
                    "out_channels": 512,
                    "kernel_size": 3,
                    "padding": 1,
                },
            ),
            (BatchNorm2dNode, {"num_features": 512}),
            LeakyReLUNode,
            (MaxPool2dNode, {"kernel_size": 2}),
            "\n",
            FlattenNode,
            (LinearNode, {"in_features": 512 * 7 * 7, "out_features": 4096}),
            LeakyReLUNode,
            (LinearNode, {"in_features": 4096, "out_features": 4096}),
            LeakyReLUNode,
            (LinearNode, {"in_features": 4096, "out_features": 1000}),
        ]
        x0, y0 = ctx.mouse_pos
        nodes, x, y = self.create_sequential(
            ctx.mouse_pos[0], ctx.mouse_pos[1], node_types, gap=3
        )

        inputs = {"image": cast(InputPort, nodes[0].in_ports[0])}
        outputs = {"class pred": cast(OutputPort, nodes[-1].out_ports[0])}

        self.wrap_with_network(inputs, outputs, x0, y0, x, y, "VGG16-BN")

    @command("Create network: ResNet18")
    def create_resnet_18(self, ctx: CommandCtx):
        """Create a ResNet18 network using basic blocks without pre-built residual blocks,
        and manually perform skip connections with AdditionNode.

        Args:
            ctx (CommandCtx): Command context.
        """
        name = self.net.next_name("ResNet18")

        x, y = ctx.mouse_pos

        resnet = ResNet(
            grapycal_torch=self,
            layers=[2, 2, 2, 2],
            start_x_pos=x,
            start_y_pos=y,
            spacing=5,
        )
        resnet.connect_internal()

        inputs = {"image": cast(InputPort, resnet.conv1.in_ports[0])}
        outputs = {"class pred": cast(OutputPort, resnet.layer4[-1].relu2.out_ports[0])}

        # Wrap with network
        self.wrap_with_network(
            inputs,
            outputs,
            ctx.mouse_pos[0],
            ctx.mouse_pos[1],
            resnet.x,
            resnet.y,
            name,
        )

class ImageDataset(torch.utils.data.Dataset): # type: ignore
    """
    Loads all images from a directory into memory
    """

    def __init__(self, directory: str, transform=None, max_size=None, format="jpg"):
        super().__init__()
        self.directory = directory
        self.transform = transform
        self.format = format
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
                return plt.imread(io.BytesIO(await f.read()), format=self.format)

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
        self.format = self.add_text_control("", "format", name="image_format")

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

class CatDogDataset(torch.utils.data.Dataset):
    """
    Crawl Cat and Dog images and load them into memory
    - https://cataas.com/cat
        - response is : `image/*`
    - https://dog.ceo/api/breeds/image/random Fetch!
        - response is : `application/json`
            ```
            {
                "message": "https://images.dog.ceo/breeds/terrier-tibetan/n02097474_5996.jpg",
                "status": "success"
            }
            ```
    - Reference:
    - https://hackmd.io/@lido2370/S1aX6e1nN?type=view

    TODO:
    - return : torch.utils.data.Dataset[(image, label)]
    - reference : MNIST Dataset
    """

    def __init__(self, transform=None,cat_size=500,dog_size=500):
        super().__init__()
        self.cat_size = cat_size
        self.dog_size = dog_size
        self.cat_url = "https://cataas.com/cat"
        self.dog_url = "https://dog.ceo/api/breeds/image/random"
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
        self.ds = asyncio.run(self.load_dataset())

    async def load_dataset(self):
        # concurrent loading from disk using aiofiles
        async def fetch_dog():
            async with aiohttp.ClientSession() as session:
                async with session.get(self.dog_url) as response:
                    data = await response.json()
                    url = data["message"]
                    async with session.get(url) as response:
                        content_type = response.headers.get("content-type")
                        content_type = content_type.split("/")[1]
                        return plt.imread(io.BytesIO(await response.read()), format=content_type)
                
        async def fetch_cat():
            async with aiohttp.ClientSession() as session:
                async with session.get(self.cat_url) as response:
                    content_type = response.headers.get("content-type")
                    content_type = content_type.split("/")[1]
                    return plt.imread(io.BytesIO(await response.read()), format=content_type)
                
        async def fetch_image(type):
            image = await fetch_cat() if type == 0 else await fetch_dog()
            return image, type
                
        # cat:0
        # dog:1
        # random sequence of cat_size of 0 and dog_size of 1
        sequence = [0] * self.cat_size + [1] * self.dog_size
        np.random.shuffle(sequence)
        tasks = []

        for type in sequence:
            tasks.append(fetch_image(type))

        return await asyncio.gather(*tasks)

    def __len__(self):
        return len(self.ds)

    def __getitem__(self, idx):
        img,label = self.ds[idx]
        if self.transform:
            img = self.transform(img)
        return img,label

class CatDogDatasetNode(SourceNode):
    """
    Crawl Cat and Dog images from:
    - https://cataas.com/cat
        - response is : `image/*`
    - https://dog.ceo/api/breeds/image/random Fetch!
        - response is : `application/json`
            ```
            {
                "message": "https://images.dog.ceo/breeds/terrier-tibetan/n02097474_5996.jpg",
                "status": "success"
            }
            ```
    """

    category = "torch/dataset"
    
    def build_node(self):
        super().build_node()
        self.label.set("Cat Dog Dataset")
        self.cat_size = self.add_text_control("500", "cat_size", name="cat_size")
        self.dog_size = self.add_text_control("500", "dog_size", name="dog_size")
        self.out = self.add_out_port("Image Dataset")

    def init_node(self):
        super().init_node()
        self.ds = None

    def task(self):
        self.ds = CatDogDataset(cat_size=int(self.cat_size.get()),dog_size=int(self.dog_size.get()))
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
