

from typing import TYPE_CHECKING

import torch

if TYPE_CHECKING:
    from grapycal_torch.settings import SettingsNode

    from .manager import MNManager, NetManager

class GrapycalTorchStore:
    def __init__(self, mn: 'MNManager', net: 'NetManager'):
        self.mn = mn
        self.net = net
        self.settings: 'SettingsNode'

    def to_tensor(self, data, device:str='default'):
        if device == 'default':
            device = self.settings.default_device.get()
        return torch.tensor(data, device=device)
    
    def get_device(self, device:str='default'):
        if device == 'default':
            return self.settings.default_device.get()
        return device