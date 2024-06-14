from abc import abstractmethod
from typing import TYPE_CHECKING, Any, final

from grapycal import EventTopic, task
from grapycal.extension_api.trait import Parameter, ParameterTrait
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.node import Node
from grapycal.sobjects.port import InputPort
from objectsync import StringTopic
from torch import Tensor, nn

from grapycal_torch.store import GrapycalTorchStore

from .settings import SettingsNode

if TYPE_CHECKING:
    from grapycal_torch import GrapycalTorch


class ModuleMover:
    """
    Moves a module or a tensor to a device, but asynchronusly
    """

    def __init__(self):
        self._actual_device = "default"
        self._target_device = "default"

    def set_target_device(self, device):
        self._target_device = device

    def set_actual_device(self, device):
        self._actual_device = device

    def get_target_device(self, translate=True):
        if translate:
            return self.translate(self._target_device)
        return self._target_device

    def translate(self, device: str):
        if device == "default":
            device = SettingsNode.instance.default_device.get()
        if device == "cuda":
            return "cuda:0"
        return device

    def move_if_needed(self, module_or_tensor: nn.Module | Tensor):
        real_target = self.translate(self._target_device)
        if real_target != self._actual_device:
            module_or_tensor.to(real_target)
            self._actual_device = real_target
            return True
        return False


class ModuleNode(Node):
    """
    state_dict_id is used to identify the module when saving and loading state dicts. When loading from file, its value must match what it was when the state dict was saved.
    """

    ext: "GrapycalTorch"
    category = "torch/neural network"
    icon_path = "nn"

    def build_node(self):
        # TODO: save and load
        self.shape.set("simple")
        self.label.set("Module")
        self.create_module_topic = self.add_attribute(
            "reset", EventTopic, editor_type="button", is_stateful=False
        )

        # the node's id changes when it's loaded from a file, so it needs another id to identify the state dict
        # initialized by manager and can be modified by the user
        self.state_dict_id = self.add_attribute(
            "state_dict_id", StringTopic, "", editor_type="text"
        )

    def init_node(self):
        self.torch_store = self.get_store(GrapycalTorchStore)
        self.module: nn.Module | None = None
        self.create_module_topic.on_emit.add_manual(self.create_module_task)
        self.module_mover = ModuleMover()
        self.torch_store.mn.add(self)

    @task
    def create_module_task(self):
        self.module = self.create_module()
        self.module_mover.set_actual_device("cpu")
        num_params = sum(p.numel() for p in self.module.parameters() if p.requires_grad)
        if num_params >= 1000000:
            param_str = f"{num_params/1000000:.1f}M"
        elif num_params >= 1000:
            param_str = f"{num_params/1000:.1f}K"
        else:
            param_str = f"{num_params}"
        self.print("created module", self.module, "\nparameters:", param_str)

    def to(self, device):
        self.module_mover.set_target_device(device)

    @abstractmethod
    def create_module(self) -> nn.Module:
        pass

    @abstractmethod
    def forward(self):
        """
        Consume the input from the input ports, run a forward pass, and output the result to the output ports
        """
        pass

    def edge_activated(self, edge: Edge, port: InputPort):
        for port_ in self.in_ports:
            if not port_.is_all_ready():
                return
        self.run(self.task)

    def task(self):
        if self.module is None:
            self.create_module_task()
        if self.module_mover.move_if_needed(self.module):  # type: ignore
            self.print("moved to", self.module_mover.get_target_device())
        self.forward()

    def get_module(self) -> nn.Module:
        assert self.module is not None
        return self.module

    def get_device(self) -> str:
        return self.module_mover.get_target_device(False)

    def set_mode(self, mode):
        if self.module is None:
            return
        if mode == "train":
            self.module.train()
            self.module.requires_grad_(True)
        elif mode == "eval":
            self.module.eval()
            self.module.requires_grad_(False)

    def get_state_dict(self):
        if self.module is None:
            self.create_module_task()
        return self.module.state_dict()

    def load_state_dict(self, state_dict):
        if self.module is None:
            self.create_module_task()
        self.module.load_state_dict(state_dict)

    def destroy(self):
        self.torch_store.mn.remove(self)
        return super().destroy()


class SimpleModuleNode(ModuleNode):
    module_type: type[nn.Module] = nn.Module
    inputs: list[str] = ["input"]
    max_in_degree = [1]
    outputs = ["output"]
    display_port_names: bool | None = None
    hyper_parameters = []
    """
    define the hyper parameters of the module. They will be passed in the constructor of the module.

        Example::

            return [
                Parameter("in_channels", "int", 1),
                Parameter("out_channels", "int", 1),
                Parameter("kernel_size", "str", "3"),
                Parameter("padding", "str", "1"),
                Parameter("stride", "str", "1"),
                Parameter("dilation", "str", "1"),
            ]
    """

    def define_traits(self):
        self.parameter_trait = ParameterTrait(self.define_hyper_parameters())
        self.parameter_trait.on_update += self.parameter_changed
        return [
            self.parameter_trait,
        ]

    def detect_inputs(self) -> list[str]:
        func = self.module_type.forward
        if hasattr(func, "__annotations__"):
            return list(func.__annotations__.keys() - {"return"})
        return ["input"]

    def build_node(self, *args, **kwargs):
        super().build_node()
        if self.inputs == []:
            self.inputs = self.detect_inputs()
        self._max_in_degree = self.max_in_degree[:]
        while len(self._max_in_degree) < len(self.inputs):
            self._max_in_degree.append(1)
        for i in range(len(self._max_in_degree)):
            if self._max_in_degree[i] is None:
                self._max_in_degree[i] = 64

        if self.display_port_names is None:
            self.display_port_names = len(self.inputs) > 1 or len(self.outputs) > 1

        for name, max_edges in zip(self.inputs, self._max_in_degree):  # type: ignore
            display_name = name if self.display_port_names else ""
            self.add_in_port(name, max_edges, display_name=display_name)
        for name in self.outputs:
            display_name = name if self.display_port_names else ""
            self.add_out_port(name, display_name=display_name)

    def init_node(self):
        super().init_node()
        self._param_dirty = True
        self.parameter_changed(self.parameter_trait.get_values())

    def task(self):
        if self._param_dirty:
            self.create_module_task()
        if self.module_mover.move_if_needed(self.module):  # type: ignore
            self.print("moved to", self.module_mover.get_target_device())

        inputs = {}
        for port in self.in_ports:
            inp = port.get()
            if (
                isinstance(inp, Tensor)
                and str(inp.device) != self.module_mover.get_target_device()
            ):
                if inp.requires_grad:
                    self.print_exception(
                        f"Cannot implicitly move input tensor {port.name.get()} from device {inp.device} to a different device {self.module_mover.get_target_device()} where the module is because it requires grad. Please move it manually if you intend to do so.",
                        clear_graph=True,
                    )
                    return
                inp = inp.to(self.module_mover.get_target_device())
            inputs[port.name.get()] = inp

        result = self.forward(**inputs)

        if len(self.out_ports) == 1:
            self.out_ports[0].push(result)
        else:
            for port, data in zip(self.out_ports, result):
                port.push(data)

    @final
    def create_module(self) -> nn.Module:
        self._param_dirty = False
        return self.module_type(**self.parameter_trait.get_values())

    def forward(self, **inputs) -> Any:
        """
        Override to define the forward pass of the module. The inputs are passed as keyword arguments.
        If not overridden, the default implementation will call self.module(**inputs). If there is only one input, it will call self.module(value).
        """
        if len(inputs) == 1:
            return self.module(list(inputs.values())[0])
        return self.module(**inputs)

    def define_hyper_parameters(self) -> list[Parameter]:
        return self.hyper_parameters

    def parameter_changed(self, params):
        self.label.set(self.get_label(params))
        self._param_dirty = True

    def get_label(self, params):
        return (
            self.module_type.__name__
            + " "
            + " ".join(f"{k}={v}" for k, v in params.items())
        )
