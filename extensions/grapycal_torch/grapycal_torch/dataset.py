from pathlib import Path
from typing import Callable
from grapycal.extension_api.trait import OutputsTrait, Chain, TriggerTrait
from grapycal.sobjects.controls.sliderControl import SliderControl
import torch.utils.data
import torchvision
from grapycal import SourceNode, Node
from grapycal.stores import main_store
from torchvision import transforms
from grapycal import get_resource, background_task
from PIL import Image


class MnistDatasetNode(SourceNode):
    category = "torch/dataset"

    def build_node(self):
        super().build_node()
        self.label_topic.set("MNIST Dataset")
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


class ImageDataset(torch.utils.data.Dataset):
    """
    A dataset with images.
    """

    def __init__(
        self,
        path: str | Path,
        pre_transform: Callable | None = None,
        post_transform: Callable | None = None,
    ):
        self.path = Path(path)
        self.pre_transform = pre_transform or transforms.ToTensor()
        self.post_transform = post_transform or (lambda x: x)
        self.images = []
        self.do_augment = True
        if self.path.is_dir():
            self.load_from_folder()
        else:
            self.load_from_zip()

    def load_from_zip(self):
        import zipfile

        with zipfile.ZipFile(self.path, "r") as zip_ref:
            for name in zip_ref.namelist():
                if name.endswith(".jpg") or name.endswith(".png"):
                    with zip_ref.open(name) as f:
                        self.images.append(self.pre_transform(Image.open(f)))

    def load_from_folder(self):
        for file in self.path.iterdir():
            if file.is_file() and file.suffix in [".jpg", ".png"]:
                self.images.append(self.pre_transform(Image.open(file)))

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        if self.do_augment:
            return self.post_transform(self.images[idx])
        return self.images[idx]


class ImageDatasetNode(Node):
    """
    Images from the Linnaeus 5 dataset
    """

    img_classes = {
        "berry": "download/image/Linnaeus5/train/berry.zip",
        "bird": "download/image/Linnaeus5/train/bird.zip",
        "dog": "download/image/Linnaeus5/train/dog.zip",
        "flower": "download/image/Linnaeus5/train/flower.zip",
        "other": "download/image/Linnaeus5/train/other.zip",
    }

    def define_traits(self):
        return Chain(
            TriggerTrait(),
            self.get_dataset,
            OutputsTrait(),
        )

    def build_node(self):
        self.class_control = self.add_option_control(
            name="class",
            options=list(self.img_classes.keys()),
            value="dog",
            label="class",
        )
        self.size_port = self.add_in_port(
            "size",
            1,
            control_type=SliderControl,
            min=1,
            max=256,
            value=256,
            int_mode=True,
        )

    @background_task
    def get_dataset(self):
        class_name = self.class_control.get()
        path = self.img_classes[class_name]
        path = get_resource(path)
        size = self.size_port.get()

        dataset = ImageDataset(
            path,
            pre_transform=transforms.Compose([transforms.ToTensor()]),
            post_transform=transforms.Compose(
                [
                    # transforms.RandomAffine(
                    #     15, translate=(0.05, 0.05), scale=(1.2, 1.3)
                    # ),
                    # transforms.RandomHorizontalFlip(),
                    transforms.Resize((size, size)),
                ]
            ),
        )
        return dataset
