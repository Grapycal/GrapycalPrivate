from grapycal.extension.utils import NodeInfo
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.node import singletonNode
from grapycal.sobjects.port import InputPort
from grapycal.stores import main_store
from objectsync.sobject import SObjectSerialized
from .printNode import *
from .evalNode import *
from .execNode import *
from .imagePasteNode import *

class LabelNode(Node):
    category = 'interaction'
    def build_node(self):
        self.shape.set('simple')
        self.css_classes.append('fit-content')
        self.expose_attribute(self.label, editor_type='text')
        self.restore_attributes('label')

@singletonNode(auto_instantiate=False)
class WebcamNode(Node):
    category = 'interaction'

    def build_node(self):
        self.label.set('Webcam')
        self.shape.set('simple')
        self.format = self.add_attribute('format',StringTopic,'numpy',editor_type='options',options=['torch','numpy'])
        self.out_port = self.add_out_port('img')
        self.button = self.add_button_control('Start streamimg','button')

    def init_node(self):
        if self.is_preview.get():
            return
        self.webcam = main_store.webcam
        if not self.is_preview.get():
            self.webcam.image.on_set.add_manual(self._on_image_set)
        self.webcam.source_client.on_set.add_manual(self._source_client_changed)
        self.button.on_click.add_manual(self._btn)

    def _btn(self):
        if self.webcam.source_client.get() == self._server.get_action_source():
            self.webcam.source_client.set(-1)
        else:
            self.webcam.source_client.set(self._server.get_action_source())

    def _source_client_changed(self,source_client:int):
        if source_client == -1:
            self.button.label.set('Start streamimg')
        else:
            self.button.label.set('Streaming from: '+str(source_client))

    def _on_image_set(self,_):
        if len(self.out_port.edges) == 0:
            return
        self.run(self._on_image_set_task)

    def _on_image_set_task(self):
        image_bytes:bytes = main_store.webcam.image.to_binary()
        img = Image.open(io.BytesIO(image_bytes))
        # comvert image to torch or numpy
        if self.format.get() == 'torch':
            img = torch.from_numpy(np.array(img))
            img = img.permute(2,0,1).to(torch.float32)/255
            if img.shape[0] == 4:
                img = img[:3]
        elif self.format.get() == 'numpy':
            img = np.array(img).astype(np.float32).transpose(2,0,1)/255
            if img.shape[0] == 4:
                img = img[:3]

        self.out_port.push(img)

    def destroy(self) -> SObjectSerialized:
        if not self.is_preview.get():
            self.webcam.image.on_set.remove(self._on_image_set)
            self.webcam.source_client.on_set.remove(self._source_client_changed)
        return super().destroy()

class TriggerNode(Node):
    category = 'interaction'
    def build_node(self):
        self.shape.set('simple')
        self.label.set('Trigger')
        self.css_classes.append('fit-content')
        self.add_out_port('Trigger',display_name='')

    def double_click(self):
        self.out_ports[0].push(None)
