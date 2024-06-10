from grapycal import Extension
from grapycal.stores import main_store
from .utils import Clock
from grapycal import Node
from .pianoroll import PianoRoll

from .input import *
from .output import *
from .synth import *
from .signal import *
from .filter import *

del Node


class GrapycalAudio(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_size = 1024
        self.sample_rate = 22050
        self.chunk_duration = self.chunk_size / self.sample_rate
        self.clock = Clock(40 / 1000)
        main_store.event_loop.create_task(self.clock.run())
