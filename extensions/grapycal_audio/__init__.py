from grapycal import Extension
from grapycal.stores import main_store
from .utils import Clock
from grapycal import Node

from .output import *
from .synth import *
from .signal import *
from .filter import *

del Node

class GrapycalAudio(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_size = 4096
        self.sample_rate = 44100
        self.chunk_duration = self.chunk_size / self.sample_rate
        self.clock = Clock(100/1000)
        main_store.event_loop.create_task(self.clock.run())
