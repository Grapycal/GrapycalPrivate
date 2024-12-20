from grapycal import IntTopic, Node
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import InputPort
from grapycal.stores import main_store
from grapycal_torch.store import GrapycalTorchStore
from topicsync.topic import GenericTopic
from torch import Tensor
from torch.utils.data import DataLoader


class DataLoaderNode(Node):
    category = "torch/dataloader"

    def build_node(self):
        super().build_node()
        self.label_topic.set("DataLoader")
        self.shape_topic.set("simple")
        self.dataset = self.add_in_port("dataset")
        self.num_epochs = self.add_attribute("epochs", IntTopic, 1, editor_type="int")
        self.batch_size = self.add_attribute(
            "batch_size", IntTopic, 1, editor_type="int"
        )
        self.shuffle = self.add_attribute("shuffle", IntTopic, 0, editor_type="int")
        self.num_workers = self.add_attribute(
            "num_workers", IntTopic, 0, editor_type="int"
        )
        self.out = self.add_out_port("batch")
        self.status_control = self.add_text_control(
            name="status_control", readonly=True, text="[idle]"
        )
        self.to_defalut_device = self.add_attribute(
            "to_default_device", GenericTopic[bool], True, editor_type="toggle"
        )

    def init_node(self):
        super().init_node()
        self.dl: DataLoader | None = None
        self.double_clicked = False

    def task(self):
        self.double_clicked = False
        dataset = self.dataset.get()
        batch_size = self.batch_size.get()
        shuffle = self.shuffle.get() == 1
        num_workers = self.num_workers.get()
        self.dl = DataLoader(
            dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers
        )
        for i in range(self.num_epochs.get()):
            self.status_control.set("epoch: " + str(i))
            for batch in self.dl:
                if self.double_clicked:
                    self.double_clicked = False
                    self.status_control.set("")
                    main_store.send_message_to_all(
                        "DataLoader interrupted at epoch " + str(i)
                    )
                    return
                if self.to_defalut_device.get():
                    if isinstance(batch, dict):
                        for key in batch:
                            if isinstance(batch[key], Tensor):
                                batch[key] = self.get_store(
                                    GrapycalTorchStore
                                ).to_default_device(batch[key])
                    elif isinstance(batch, Tensor):
                        batch = self.get_store(GrapycalTorchStore).to_default_device(
                            batch
                        )
                    else:
                        pass
                self.out.push(batch)
                self.flash_running_indicator()
                yield
        self.status_control.set("")

    def edge_activated(self, edge: Edge, port: InputPort):
        self.run(self.task)

    def icon_clicked(self):
        # stop the task
        self.double_clicked = True
