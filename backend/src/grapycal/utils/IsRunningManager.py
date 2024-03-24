from grapycal.extension.utils import Clock
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.node import Node
from objectsync import ObjSetTopic


import threading


class IsRunningManager:
    def __init__(self, running_nodes_topic: ObjSetTopic, clock:Clock):
        self._running_nodes_topic = running_nodes_topic
        self._set_running_true = set()
        self._set_running_true_2 = set()
        self._running = set()
        self._set_running_lock = threading.Lock()

        clock.on_tick += self.check_running_nodes

    def check_running_nodes(self):
        with self._set_running_lock:
            self._running_nodes_topic.set(list(self._running | self._set_running_true | self._set_running_true_2))
            self._set_running_true_2 = self._set_running_true
            self._set_running_true = set()

    def set_running(self, node: Node|Edge, running: bool):
        with self._set_running_lock:
            if running:
                self._set_running_true.add(node)
                self._running.add(node)
            else:
                self._running.discard(node)