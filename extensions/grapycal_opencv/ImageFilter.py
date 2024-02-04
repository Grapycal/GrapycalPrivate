from grapycal import Node
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import InputPort
import numpy as np


class ImageFilter(Node):
    category = "opencv"

    def build_node(self):
        self.label.set("Image Filter")
        self.shape.set("simple")
        self.text = self.add_text_control("0")
        self.prev_button = self.add_button_control("Previous")
        self.next_button = self.add_button_control("Next")
        self.output_port = self.add_out_port("Image Output")
        self.input_port = self.add_in_port("Images Input")
        self.index = 0
        self.image_num = 0
        self.images = None

    def init_node(self):
        self.index = 0
        self.image_num = 0
        self.prev_button.on_click += self.prev_button_clicked
        self.next_button.on_click += self.next_button_clicked

    def prev_button_clicked(self):
        if self.index == 0:
            return
        self.index -= 1
        self.text.set(str(self.index + 1) + " / " + str(self.image_num))
        self.run(self.push_image)

    def next_button_clicked(self):
        if self.index == self.image_num - 1:
            return
        self.index += 1
        self.text.set(str(self.index + 1) + " / " + str(self.image_num))
        self.run(self.push_image)

    def edge_activated(self, edge: Edge, port: InputPort):
        self.images = self.input_port.get_one_data()
        self.image_num = len(self.images)
        self.index = 0
        print()
        self.text.set(str(self.index + 1) + " / " + str(self.image_num))
        self.run(self.init_image)

    def init_image(self):
        image = np.array(self.images[0]).astype(np.float32).transpose(2, 0, 1) / 255
        image = image[::-1, :, :]
        if image.shape[0] == 4:
            image = image[:3]
        self.output_port.push_data(image)

    def push_image(self):
        image = (
            np.array(self.images[self.index]).astype(np.float32).transpose(2, 0, 1)
            / 255
        )
        image = image[::-1, :, :]
        if image.shape[0] == 4:
            image = image[:3]
        self.output_port.push_data(image)