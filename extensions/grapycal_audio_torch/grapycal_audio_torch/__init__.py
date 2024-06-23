from grapycal import Extension

from .misc import PianoRollPlayerNode

from .dataset import PianoRollDatasetNode


class GrapycalAudioTorch(Extension):
    dependencies = ["grapycal_audio", "grapycal_torch"]
    node_types = [PianoRollDatasetNode, PianoRollPlayerNode]
