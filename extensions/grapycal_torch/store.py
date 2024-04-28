

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import MNManager, NetManager


class GrapycalTorchStore:
    def __init__(self, mn: 'MNManager', net: 'NetManager'):
        self.mn = mn
        self.net = net