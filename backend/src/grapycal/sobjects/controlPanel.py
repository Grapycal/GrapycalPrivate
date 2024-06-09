from grapycal.stores import main_store
from grapycal.utils.misc import Action
from objectsync import SObject, StringTopic
from topicsync.topic import ListTopic
import logging

logger = logging.getLogger(__name__)


class ControlPanel(SObject):
    _instance: "ControlPanel"
    frontend_type = "ControlPanel"
    on_run_task = Action()

    @classmethod
    def add_task(cls, task):
        cls._instance.task_list.insert(task)

    @classmethod
    def remove_task(cls, task):
        cls._instance.task_list.remove(task)

    def build(self, old=None):
        ControlPanel._instance = self
        self.runner_status = self.add_attribute("runner_status", StringTopic)
        self.task_list = self.add_attribute("task_list", ListTopic)
        self.register_service("play", self.run_task)
        main_store.clock.add_listener(self.check_runner_state, 0.2)

    def run_task(self, task: str):
        self.on_run_task.invoke(task)

    def check_runner_state(self):
        if main_store.runner.is_idle():
            value = "idle"
        else:
            value = "running"
        if main_store.runner.is_paused():
            value += " paused"
        self.runner_status.set(value)
