import io
from grapycal.sobjects.controls.control import Control
from objectsync import StringTopic
from topicsync.topic import FloatTopic

smallest_jpg = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k="


class ImageControl(Control):
    """ """

    frontend_type = "ImageControl"

    def build(self):
        self.image = self.add_attribute(
            "image", StringTopic, smallest_jpg, is_stateful=False
        )
        self.width = self.add_attribute("width", FloatTopic, 100)
        self.height = self.add_attribute("height", FloatTopic, 100)
        self.on_image_set = self.image.on_set

    def set(self, image: bytes | io.BytesIO | None | str):
        if image is None:
            self.image.set(smallest_jpg)
            return
        if isinstance(image, io.BytesIO):
            image.seek(0)
            image = image.read()
            self.image.set_from_binary(image)
        elif isinstance(image, bytes):
            self.image.set_from_binary(image)
        elif isinstance(image, str):
            self.image.set(image)

    def get(self) -> bytes:
        return self.image.to_binary()
