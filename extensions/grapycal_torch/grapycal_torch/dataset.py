from grapycal.extension_api.trait import OutputsTrait, Chain, TriggerTrait
import torchvision
from grapycal import SourceNode, Node
from grapycal.stores import main_store
from torchvision import transforms


class MnistDatasetNode(SourceNode):
    category = "torch/dataset"

    def build_node(self):
        super().build_node()
        self.label.set("MNIST Dataset")
        self.out = self.add_out_port("MNIST Dataset")
        self.include_labels = self.add_option_control(
            name="include_labels",
            options=["True", "False"],
            value="True",
            label="Include labels",
        )
        self.size = self.add_slider_control(
            label="size", value=1000, min=1, max=60000, int_mode=True, name="size"
        )

    def task(self):
        transform = transforms.Compose(
            [
                transforms.ToTensor(),
                transforms.Resize((32, 32)),
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
            pair = raw_ds[i]
            ds.append({"image": pair[0], "label": pair[1]})

        if self.include_labels.get() == "False":
            ds = [x["image"] for x in ds]

        self.out.push(ds)


class ImageDatasetNode(Node):
    def define_traits(self):
        return Chain(
            TriggerTrait(),
            self.get_dataset,
            OutputsTrait(),
        )

    def get_dataset(self):
        return "dataset"
