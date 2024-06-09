from grapycal.stores import main_store
from objectsync import SObject, StringTopic
from topicsync.topic import ListTopic


class ControlPanel(SObject):
    frontend_type = "ControlPanel"

    def build(self, old=None):
        self.runner_status = self.add_attribute("runner_status", StringTopic)
        self.task_list = self.add_attribute("task_list", ListTopic)
        self.on("runTaskTopic", self.run_task, is_stateful=False)
        main_store.clock.add_listener(self.check_runner_state, 0.2)

    def run_task(self, task: str):
        print(f"Running task: {task}")

    def check_runner_state(self):
        if main_store.runner.is_idle():
            value = "idle"
        else:
            value = "running"
        if main_store.runner.is_paused():
            value += " paused"
        self.runner_status.set(value)
