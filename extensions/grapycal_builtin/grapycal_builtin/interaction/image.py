import io
from contextlib import contextmanager
from typing import Generator, Literal, Tuple

from grapycal.extension_api.decor import func
import matplotlib
from grapycal import FloatTopic, StringTopic, to_numpy, param
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.node import Node
from grapycal.sobjects.port import InputPort
from grapycal.sobjects.sourceNode import SourceNode
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from topicsync.topic import GenericTopic

try:
    import torch

    HAS_TORCH = True
    from torch import Tensor
except ImportError:
    HAS_TORCH = False
    Tensor = None

import numpy as np
from numpy import ndarray

try:
    from PIL import Image, ImageOps

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


plt.style.use("dark_background")
matplotlib.use("Agg")
plt.ioff()


@contextmanager
def open_fig(equal=False) -> Generator[Tuple[Figure, Axes], None, None]:
    fig = plt.figure()
    ax = fig.gca()
    ax.set_facecolor("black")
    try:
        yield fig, ax
    finally:
        plt.close(fig)


class ImageSourceNode(SourceNode):
    category = "interaction"

    def build_node(self, image: str | None = ""):
        super().build_node()
        self.shape_topic.set("simple")
        self.img = self.add_image_control(name="img")
        self.format = self.add_attribute(
            "format",
            StringTopic,
            "numpy",
            editor_type="options",
            options=["numpy", "torch"],
        )
        self.out_port = self.add_out_port("img")
        self.icon_path_topic.set("image")
        if image:
            self.img.set(image)
            self.format.add_validator(self.format_validator)

    def init_node(self):
        super().init_node()

    @param()
    def param(
        self,
        channels: Literal["gray scale", "rgb", "rgba"] = "rgb",
        resize: bool = False,
        width: int = 256,
        height: int = 256,
        resize_mode: Literal["fit", "contain"] = "fit",
    ):
        self.resize = resize
        self.width = width
        self.height = height
        self.resize_mode = resize_mode
        self.channels = channels

    def format_validator(self, format, _):
        if "torch" in format:
            if not HAS_TORCH:
                return False
            return True
        if "numpy" in format:
            return True
        return False

    def task(self):
        if not HAS_PIL:
            raise ImportError(
                "PIL is not installed. Please install PIL to use this node."
            )
        image_bytes: bytes = self.img.get()
        # convert image to PIL
        img = Image.open(io.BytesIO(image_bytes))

        if self.resize:
            if self.resize_mode == "fit":
                img = ImageOps.fit(img, (self.width, self.height))
            elif self.resize_mode == "contain":
                img = ImageOps.contain(img, (self.width, self.height))
                img = ImageOps.pad(img, (self.width, self.height))

        # comvert image to torch or numpy
        if self.format.get() == "torch":
            img = torch.from_numpy(np.array(img))
            img = img.permute(2, 0, 1).to(torch.float32) / 255
            if self.channels == "gray scale":
                img = img[:3].mean(0, keepdim=True)
            elif self.channels == "rgb":
                if img.shape[0] == 1:
                    img = torch.cat([img, img, img], dim=0)
                if img.shape[0] == 4:
                    img = img[:3]
            elif self.channels == "rgba":
                if img.shape[0] == 1:
                    img = torch.cat([img, img, img, torch.ones_like(img)], dim=0)
                if img.shape[0] == 3:
                    img = torch.cat([img, torch.ones_like(img[:1])], dim=0)

        elif self.format.get() == "numpy":
            img = np.array(img).astype(np.float32).transpose(2, 0, 1) / 255
            if self.channels == "gray scale":
                img = img[:3].mean(0, keepdims=True)
            elif self.channels == "rgb":
                if img.shape[0] == 1:
                    img = np.concatenate([img, img, img], axis=0)
                if img.shape[0] == 4:
                    img = img[:3]
            elif self.channels == "rgba":
                if img.shape[0] == 1:
                    img = np.concatenate([img, img, img, np.ones_like(img)], axis=0)
                if img.shape[0] == 3:
                    img = np.concatenate([img, np.ones_like(img[:1])], axis=0)

        self.out_port.push(img)


class Renderer:
    def __init__(self, width: int, height: int):
        self._set_size(width, height)

    def set_size(self, width, height):
        if width == self.width and height == self.height:
            return
        self.close()
        self._set_size(width, height)

    def _set_size(self, width, height):
        self.width = width
        self.height = height
        self.fig = plt.figure(
            figsize=(width / 128 * 1.299, height / 128 * 1.299),
            dpi=128,
        )  # 1.299 makes pyplot outputs correctly
        self.ax = self.fig.gca()

    def render(
        self,
        x_range: tuple[float, float] | None = None,
        y_range: tuple[float, float] | None = None,
        format="jpg",
    ) -> io.BytesIO:
        if x_range is not None:
            plt.xlim(x_range)
        if y_range is not None:
            plt.ylim(y_range)
        buf = io.BytesIO()
        self.ax.axis("off")
        self.fig.savefig(
            buf,
            format=format,
            bbox_inches="tight",
            transparent=True,
            pad_inches=0,
            dpi=128,
            facecolor=self.fig.get_facecolor(),
        )
        self.ax.clear()
        buf.seek(0)
        return buf

    def close(self):
        plt.close(self.fig)


class DisplayImageNode(Node):
    """
    Display an image from the input data
    The input data can be a numpy array or a torch tensor, with one of the following shapes:
    [..., 4 (rgba),h,w]
    [..., 3 (rgb),h,w]
    [..., 1 (grayscale),h,w]
    [..., h,w]

    The ... part can be any number of dimensions or none.

    Do not input data with shape [h,w,c] or it will display incorrectly.

    If the alpha channel is present, png format will be used, otherwise jpg format will be used.
    Get rid of alpha channel if it is not important to save network bandwidth.
    """

    category = "interaction"

    def build_node(self):
        self.label_topic.set("Display Image")
        self.shape_topic.set("simple")
        self.img_control = self.add_image_control(name="img")
        self.icon_path_topic.set("image")
        self.cmap = self.add_attribute(
            "cmap",
            StringTopic,
            "viridis",
            editor_type="options",
            options="gray,viridis,plasma,inferno,magma,cividis,Greys,Purples,Blues,Greens,Oranges,Reds,YlOrBr,YlOrRd,OrRd,PuRd,RdPu,BuPu,GnBu,PuBu,YlGnBu,PuBuGn,BuGn,YlGn,binary,gist_yarg,gist_gray,gray,bone,pink,spring,summer,autumn,winter,cool,Wistia,hot,afmhot,gist_heat,copper,PiYG,PRGn,BrBG,PuOr,RdGy,RdBu,RdYlBu,RdYlGn,Spectral,coolwarm,bwr,seismic,twilight,twilight_shifted,hsv,Pastel1,Pastel2,Paired,Accent,Dark2,Set1,Set2,Set3,tab10,tab20,tab20b,tab20c,flag,prism,ocean,gist_earth,terrain,gist_stern,gnuplot,gnuplot2,CMRmap,cubehelix,brg,gist_rainbow,rainbow,jet,nipy_spectral,gist_ncar".split(
                ","
            ),
        )
        self.use_vmin = self.add_attribute(
            "use vmin", GenericTopic[bool], False, editor_type="toggle"
        )
        self.vmin = self.add_attribute("vmin", FloatTopic, 0, editor_type="float")
        self.use_vmax = self.add_attribute(
            "use vmax", GenericTopic[bool], False, editor_type="toggle"
        )
        self.vmax = self.add_attribute("vmax", FloatTopic, 1, editor_type="float")
        self.slice = self.add_text_control(label="slice: ", name="slice", text=":")
        self.format = self.add_attribute(
            "format", StringTopic, "jpg", editor_type="options", options=["jpg", "png"]
        )

    @param()
    def param(self, width: int = 256, height: int = 256):
        if hasattr(self, "renderer"):
            self.renderer.set_size(width, height)
        else:
            self.renderer = Renderer(width, height)

    def find_valid_slice(self, data: np.ndarray) -> str | None:
        if data.ndim == 2:
            return ":"
        if data.ndim == 3 and data.shape[0] in [1, 3, 4]:
            return ":"
        if data.ndim >= 3 and data.shape[-3] == 3:
            return ("0," * (data.ndim - 3))[:-1]
        if data.ndim >= 3 and data.shape[-3] == 4:
            return ("0," * (data.ndim - 3))[
                :-1
            ]  # ignore alpha channel because the front end does not support it
        if data.ndim >= 3:
            return ("0," * (data.ndim - 2))[:-1]
        return None

    def is_valid_image(self, data: np.ndarray) -> bool:
        """
        Must be one of the following:
        [4 (rgba),h,w]
        [3 (rgb),h,w]
        [1 (grayscale),h,w]
        [h,w]
        """
        if data.ndim == 3 and data.shape[0] in [1, 3, 4]:
            return True
        if data.ndim == 2:
            return True
        return False

    def preprocess_data(self, data):
        if HAS_TORCH and isinstance(data, torch.Tensor):
            data = data.detach().cpu().numpy()

        if isinstance(data, list):
            data = np.array(
                data
            )  # stack them into array to be compatible with the next if statement

        if isinstance(data, np.ndarray):
            # Ignore all dimensions with size 1 (except last 2 dimensions)
            while data.ndim > 2 and data.shape[0] == 1:
                data = data[0]
            # Let user specify which image to display
            slice_string = self.slice.text.get()

            unsliced_data = data
            try:
                data = eval(f"unsliced_data[{slice_string}]", globals(), locals())
            except Exception:
                self.slice.text.set(":")
                pass
            if data.ndim == 2:
                pass
            else:
                slice_string = self.find_valid_slice(unsliced_data)
                if slice_string is None:
                    raise ValueError(f"Cannot display image with shape {data.shape}")
                data = eval(f"unsliced_data[{slice_string}]", globals(), locals())
                if not self.is_valid_image(data):
                    raise ValueError(f"Cannot display image with shape {data.shape}")
                self.slice.text.set(slice_string)

        return data

    @func()
    def img(self, data):
        data = self.preprocess_data(data)
        # use plt to convert to jpg

        # chw -> hwc
        if data.ndim == 3:
            data = data.transpose(1, 2, 0)
        self.renderer.ax.imshow(
            data,
            cmap=self.cmap.get(),
            vmin=self.vmin.get() if self.use_vmin.get() else None,
            vmax=self.vmax.get() if self.use_vmax.get() else None,
        )
        buf = self.renderer.render(format=self.format.get())
        self.img_control.set(buf)
        return buf

    def input_edge_removed(self, edge: Edge, port: InputPort):
        self.img_control.set(None)

    def destroy(self):
        self.renderer.close()
        return super().destroy()


class BarPlotNode(Node):
    category = "interaction"

    def build_node(self):
        self.label_topic.set("Bar Plot")
        self.shape_topic.set("simple")
        self.img = self.add_image_control(name="img")
        self.in_port = self.add_in_port("data", 64, "")

    @param()
    def param(self, width: int = 256, height: int = 256):
        if hasattr(self, "renderer"):
            self.renderer.set_size(width, height)
        else:
            self.renderer = Renderer(width, height)

    def port_activated(self, port: InputPort):
        self.run(self.render, data=port.get())

    def render(self, data):
        if isinstance(data, tuple):
            data = list(data)
        data = to_numpy(data)
        while data.ndim > 1 and data.shape[0] == 1:
            data = data[0]
        if data.ndim != 1:
            raise ValueError(f"Cannot plot with shape {data.shape}")
        self.renderer.ax.bar(range(len(data)), data * 50)
        buf = self.renderer.render()
        self.img.set(buf)
        buf.close()

    def destroy(self):
        self.renderer.close()
        return super().destroy()


class ScatterPlotNode(Node):
    category = "interaction"

    def build_node(self):
        self.label_topic.set("Scatter Plot")
        self.shape_topic.set("simple")
        self.img = self.add_image_control(name="img")
        self.slice = self.add_text_control(label="slice: ", name="slice", text=":")
        self.in_port = self.add_in_port("data", 64, "")

    @param()
    def param(self, width: int = 256, height: int = 256):
        if hasattr(self, "renderer"):
            self.renderer.set_size(width, height)
        else:
            self.renderer = Renderer(width, height)

    def edge_activated(self, edge: Edge, port: InputPort):
        if self.in_port.is_all_ready():
            self.run(self.update_image, data=self.in_port.get_all())

    def find_valid_slice(self, data: np.ndarray) -> str | None:
        if data.ndim == 2:
            return ":"
        if data.ndim >= 3:
            return ("0," * (data.ndim - 2))[:-1]
        return None

    def preprocess_data(self, data):
        if HAS_TORCH and isinstance(data, torch.Tensor):
            data = data.detach().cpu().numpy()

        if isinstance(data, np.ndarray):
            # Ignore all dimensions with size 1 (except last 2 dimensions)
            while data.ndim > 2 and data.shape[0] == 1:
                data = data[0]
            # Let user specify which image to display
            slice_string = self.slice.text.get()

            unsliced_data = data
            try:
                data = eval(f"unsliced_data[{slice_string}]", globals(), locals())
            except Exception:
                self.slice.text.set(":")

            if data.ndim == 2:
                pass

            else:
                slice_string = self.find_valid_slice(unsliced_data)
                if slice_string is None:
                    raise ValueError(f"Cannot plot with shape {data.shape}")
                data = eval(f"unsliced_data[{slice_string}]", globals(), locals())
                self.slice.text.set(slice_string)

        return data

    def update_image(self, data):
        if isinstance(data, list):
            data = np.array(data)
        for d in data:
            if len(d.shape) == 3:
                for slice in d:
                    slice = self.preprocess_data(slice)
                    self.renderer.ax.scatter(slice[:, 0], slice[:, 1], alpha=0.5)
            else:
                d = self.preprocess_data(d)
                self.renderer.ax.scatter(d[:, 0], d[:, 1], alpha=0.5)

        buf = self.renderer.render((-4, 4), (-4, 4))
        self.img.set(buf)
        buf.close()

    def input_edge_removed(self, edge: Edge, port: InputPort):
        self.img.set(None)

    def destroy(self):
        self.renderer.close()
        return super().destroy()


def to_list(data) -> list:
    if ndarray and isinstance(data, ndarray):
        data = data.tolist()
    elif Tensor and isinstance(data, Tensor):
        data = data.detach().cpu().numpy().tolist()
    elif isinstance(data, list):
        if len(data) == 0:
            return []
        elif Tensor and isinstance(data[0], Tensor):
            data = [float(d.detach().cpu()) for d in data]  # type: ignore
        elif ndarray and isinstance(data[0], ndarray):
            data = [float(d) for d in data]

    if isinstance(data, float | int):
        data = [data]
    return data


class LinePlotNode(Node):
    category = "interaction"

    def build_node(self):
        super().build_node()
        self.label_topic.set("Line Plot")
        self.shape_topic.set("simple")
        self.line_plot = self.add_lineplot_control(name="lineplot")
        self.expose_attribute(self.line_plot.lines, "list")
        self.css_classes.append("fit-content")
        self.clear_port = self.add_in_port("clear", 1)
        self.x_coord_port = self.add_in_port("x coord", 1)
        self.x_gen_mode = self.add_attribute(
            "x coord mode",
            StringTopic,
            "from 0",
            editor_type="options",
            options=["from 0", "continue"],
        )

        if self.is_new:
            self.line_plot.lines.insert("line", 0)
            self.add_line("line", None)
        else:
            for name in self.line_plot.lines:
                self.add_line(name, None)

    def init_node(self):
        self.x_coord = [0]
        self.line_plot.lines.on_insert.add_auto(self.add_line)
        self.line_plot.lines.on_pop.add_auto(self.remove_line)

    def add_line(self, name, _):
        self.add_in_port(name, 1)

    def remove_line(self, name, _):
        self.remove_in_port(name)

    def edge_activated(self, edge: Edge, port: InputPort):
        match port:
            case self.clear_port:
                port.get()
                self.line_plot.clear_all()
            case self.x_coord_port:
                self.x_coord = to_list(port.get())
            case _:
                self.run(self.update_plot, ys=port.get(), name=port.name.get())

    def gen_x_coord(self, ys):
        if self.x_gen_mode.get() == "from 0":
            return list(range(len(ys)))
        elif self.x_gen_mode.get() == "continue":
            return list(range(self.x_coord[-1] + 1, self.x_coord[-1] + len(ys) + 1))

    def update_plot(self, ys, name):
        ys = to_list(ys)
        if len(self.x_coord_port.edges) == 0 or len(ys) != len(self.x_coord):
            self.x_coord = self.gen_x_coord(ys)
            if self.x_gen_mode.get() == "from 0":
                self.line_plot.clear(name)
        xs = self.x_coord
        self.line_plot.add_points(name, xs, ys)
