from grapycal import Extension

from .dataset import PianoRollDatasetNode


class GrapycalAudioTorch(Extension):
    dependencies = ["grapycal_audio", "grapycal_torch"]
    node_types = [PianoRollDatasetNode]
