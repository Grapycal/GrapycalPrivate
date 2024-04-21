from typing import TYPE_CHECKING, List, Tuple

from grapycal import GRID
from grapycal.sobjects.port import OutputPort
from grapycal_builtin.function.math import AdditionNode

from grapycal_torch.activation import ReLUNode
from grapycal_torch.cnn import Conv2dNode
from grapycal_torch.normalize import BatchNorm2dNode
from grapycal_torch.pooling import MaxPool2dNode

if TYPE_CHECKING:
    from . import GrapycalTorch


class ResNetBasicBlock:
    expansion: int = 1
    grapycal_torch: "GrapycalTorch" = None
    conv1: Conv2dNode = None
    bn1: BatchNorm2dNode = None
    relu1: ReLUNode = None
    relu2: ReLUNode = None
    conv2: Conv2dNode = None
    bn2: BatchNorm2dNode = None
    add1: AdditionNode = None
    downsample_cnn: Conv2dNode = None
    downsample_bn: BatchNorm2dNode = None

    def __init__(
        self,
        grapycal_torch: "GrapycalTorch",
        x: float,
        y: float,
        inplanes: int,
        planes: int,
        stride: int = 1,
        downsample: Tuple[int, int] = None,  # Tuple[in_channels, out_channels]
        spacing: float = 5,
    ):
        self.grapycal_torch = grapycal_torch
        self.x = x
        self.y = y
        self.stride = stride
        self.spacing = spacing

        self.conv1 = self.grapycal_torch.create_node(
            Conv2dNode,
            [
                self.x,
                self.y,
            ],
            in_channels=inplanes,
            out_channels=planes,
            kernel_size=3,
            stride=stride,
            padding=1,
            # bias=False,
        )
        self.bn1 = self.grapycal_torch.create_node(
            BatchNorm2dNode,
            [
                self.x + GRID * 5,  # add some space
                self.y,
            ],
            num_features=planes,
        )
        self.relu1 = self.grapycal_torch.create_node(
            ReLUNode,
            [
                self.x + GRID * 12,  # add some space
                self.y,
            ],
        )
        self.conv2 = self.grapycal_torch.create_node(
            Conv2dNode,
            [
                self.x + GRID * 16,  # add some space
                self.y,
            ],
            in_channels=planes,
            out_channels=planes,
            kernel_size=3,
            stride=1,
            padding=1,
            # bias=False,
        )
        self.bn2 = self.grapycal_torch.create_node(
            BatchNorm2dNode,
            [
                self.x + GRID * 21,  # add some space
                self.y,
            ],
            num_features=planes,
        )
        self.relu2 = self.grapycal_torch.create_node(
            ReLUNode,
            [
                self.x + GRID * 32,  # add some space
                self.y - GRID * 3,  # add some space vertically
            ],
        )

        # Skip connection
        if downsample is not None:
            self.downsample_cnn = self.grapycal_torch.create_node(
                Conv2dNode,
                [
                    self.x + GRID * 12,  # add some space
                    self.y - GRID * 3,  # add some space vertically
                ],
                in_channels=downsample[0],
                out_channels=downsample[1],
                kernel_size=1,
                stride=stride,
                # bias=False,
            )
            self.downsample_bn = self.grapycal_torch.create_node(
                BatchNorm2dNode,
                [
                    self.x + GRID * 18,  # add some space
                    self.y - GRID * 3,  # add some space vertically
                ],
                num_features=downsample[1],
            )
        self.add1 = self.grapycal_torch.create_node(
            AdditionNode,
            [
                self.x + GRID * 28,  # add some space
                self.y - GRID * 3,  # add some space vertically
            ],
        )

    def connect_internal(self, prev_output: OutputPort) -> OutputPort:
        """
        Connect the internal nodes of the block

        Args:
            prev_output (OutputPort): the output port of the previous node

        Returns:
            OutputPort: the output port of the last node in the block
        """
        # Connect without skip connection first
        self.grapycal_torch.create_edge(prev_output, self.conv1.in_ports[0])
        self.grapycal_torch.create_edge(self.conv1.out_ports[0], self.bn1.in_ports[0])
        self.grapycal_torch.create_edge(self.bn1.out_ports[0], self.relu1.in_ports[0])
        self.grapycal_torch.create_edge(self.relu1.out_ports[0], self.conv2.in_ports[0])
        self.grapycal_torch.create_edge(self.conv2.out_ports[0], self.bn2.in_ports[0])
        self.grapycal_torch.create_edge(self.bn2.out_ports[0], self.add1.in_ports[0])

        # Connect skip connection
        if self.downsample_cnn is not None:
            self.grapycal_torch.create_edge(
                prev_output, self.downsample_cnn.in_ports[0]
            )
            self.grapycal_torch.create_edge(
                self.downsample_cnn.out_ports[0], self.downsample_bn.in_ports[0]
            )
            self.grapycal_torch.create_edge(
                self.downsample_bn.out_ports[0], self.add1.in_ports[0]
            )
        else:
            self.grapycal_torch.create_edge(prev_output, self.add1.in_ports[0])

        # Connect the concatenation result to the final ReLU
        self.grapycal_torch.create_edge(self.add1.out_ports[0], self.relu2.in_ports[0])

        return self.relu2.out_ports[0]


class ResNet:
    def __init__(
        self,
        grapycal_torch: "GrapycalTorch",
        layers: List[int],
        start_x_pos: float,
        start_y_pos: float,
        spacing: float = 5,
    ):
        self.grapycal_torch = grapycal_torch
        self.inplanes = 64
        self.spacing = spacing
        self.layers = layers
        self.current_x_pos = start_x_pos
        self.current_y_pos = start_y_pos
        self.x = start_x_pos
        self.y = start_y_pos
        self.conv1 = self.grapycal_torch.create_node(
            Conv2dNode,
            [self.current_x_pos, self.current_y_pos],
            in_channels=3,
            out_channels=self.inplanes,
            kernel_size=7,
            stride=2,
            padding=3,
            # bias=False,
        )
        self.bn1 = self.grapycal_torch.create_node(
            BatchNorm2dNode,
            [
                self.current_x_pos + GRID * 7,  # add some space
                self.current_y_pos,
            ],
            num_features=self.inplanes,
        )
        self.relu = self.grapycal_torch.create_node(
            ReLUNode,
            [
                self.current_x_pos + GRID * 14,  # add some space
                self.current_y_pos,
            ],
        )
        self.maxpool = self.grapycal_torch.create_node(
            MaxPool2dNode,
            [
                self.current_x_pos + GRID * 21,  # add some space
                self.current_y_pos,
            ],
            kernel_size=3,
            stride=2,
            # padding=1,
        )
        self.layer1 = self._mk_layer(
            64,
            layers[0],
            self.current_x_pos,
            self.current_y_pos + GRID * (15 * 0 + 7),
            spacing=self.spacing,
        )
        self.layer2 = self._mk_layer(
            128,
            layers[1],
            self.current_x_pos,
            self.current_y_pos + GRID * (15 * 1 + 7),
            spacing=self.spacing,
        )
        self.layer3 = self._mk_layer(
            256,
            layers[2],
            self.current_x_pos,
            self.current_y_pos + GRID * (15 * 2 + 7),
            spacing=self.spacing,
        )
        self.layer4 = self._mk_layer(
            512,
            layers[3],
            self.current_x_pos,
            self.current_y_pos + GRID * (15 * 3 + 7),
            spacing=self.spacing,
        )

    def connect_internal(self):
        self.grapycal_torch.create_edge(self.conv1.out_ports[0], self.bn1.in_ports[0])
        self.grapycal_torch.create_edge(self.bn1.out_ports[0], self.relu.in_ports[0])
        self.grapycal_torch.create_edge(
            self.relu.out_ports[0], self.maxpool.in_ports[0]
        )
        prev_output = self.maxpool.out_ports[0]
        for layer in self.layer1:
            prev_output = layer.connect_internal(prev_output)
        for layer in self.layer2:
            prev_output = layer.connect_internal(prev_output)
        for layer in self.layer3:
            prev_output = layer.connect_internal(prev_output)
        for layer in self.layer4:
            prev_output = layer.connect_internal(prev_output)

    def _mk_layer(
        self,
        planes: int,
        blocks: int,
        x_pos: float,
        y_pos: float,
        stride: int = 1,
        spacing: float = 5,
    ):
        downsample = None
        # Assume the expansion is always 1
        if stride != 1 or self.inplanes != planes * 1:
            downsample = (self.inplanes, planes * ResNetBasicBlock.expansion)

        nodes: List[ResNetBasicBlock] = []
        nodes.append(
            ResNetBasicBlock(
                self.grapycal_torch,
                x_pos,
                y_pos,
                self.inplanes,
                planes,
                stride,
                downsample,
                spacing,
            )
        )
        self.inplanes = planes * ResNetBasicBlock.expansion
        for i in range(1, blocks):
            nodes.append(
                ResNetBasicBlock(
                    self.grapycal_torch,
                    x_pos + i * GRID * 40,  # add some space
                    y_pos,
                    self.inplanes,
                    planes,
                    spacing=spacing,
                )
            )

        self.x = max(self.x, x_pos + blocks * GRID * 36)
        self.y = max(self.y, y_pos)
        return nodes
