import logging
import queue
import signal
from collections import deque
from contextlib import contextmanager
from queue import Queue
import time
from typing import Callable, Iterator, Tuple

from .stdout_helper import orig_print

logger = logging.getLogger(__name__)

"""
On Unix, SIGUSR1 is used to interrupt the runner so ctrl-c will not be mistaken as a runner interrupt.
On Windows, SIGUSR1 is not available. We use SIGINT instead. This means that the runner will be interrupted by ctrl-c. Bad.
"""
if not hasattr(signal, "SIGUSR1"):
    RUNNER_INTERRUPT_SIGNAL = signal.SIGINT
else:
    RUNNER_INTERRUPT_SIGNAL = signal.SIGUSR1


class RunnerInterrupt(Exception):
    pass


class TaskInfo:
    def __init__(
        self,
        task: Callable | Iterator,
        exception_callback: Callable[[Exception], None] | None = None,
    ):
        self.task = task
        self.exception_callback = exception_callback


def on_exception(
    e: Exception, exception_callback: Callable[[Exception], None] | None = None
):
    if exception_callback is None:
        orig_print("No exception callback", e)
    else:
        exception_callback(e)


class BackgroundRunner:
    def __init__(self):
        self._inputs: Queue[Tuple[TaskInfo, bool]] = Queue()
        self._queue: deque[TaskInfo] = deque()
        self._stack: deque[TaskInfo] = deque()
        self._exit_flag = False
        self._is_paused = False
        self._step_mode = False
        self._is_idle = True
        signal.signal(RUNNER_INTERRUPT_SIGNAL, self.interrupt_handler)

    def push(
        self,
        task: Callable,
        to_queue: bool = True,
        exception_callback: Callable[[Exception], None] | None = None,
    ):
        self._inputs.put((TaskInfo(task, exception_callback), to_queue))

    def push_to_queue(
        self,
        task: Callable,
        exception_callback: Callable[[Exception], None] | None = None,
    ):
        self._inputs.put((TaskInfo(task, exception_callback), True))

    def push_to_stack(
        self,
        task: Callable,
        exception_callback: Callable[[Exception], None] | None = None,
    ):
        self._inputs.put((TaskInfo(task, exception_callback), False))

    def interrupt(self):
        signal.raise_signal(RUNNER_INTERRUPT_SIGNAL)

    def clear_tasks(self):
        self._queue.clear()
        self._stack.clear()

    def exit(self):
        self._exit_flag = True
        self.interrupt()

    def interrupt_handler(self, signum, frame):
        raise RunnerInterrupt

    @contextmanager
    def no_interrupt(self):
        def handler(signum, frame):
            logger.info("Cannot interrupt current task")

        try:
            signal.signal(RUNNER_INTERRUPT_SIGNAL, handler)
            yield
        finally:
            signal.signal(RUNNER_INTERRUPT_SIGNAL, self.interrupt_handler)

    def run(self):
        while True:
            if self._exit_flag:
                break
            try:
                # Queue.get() blocks signal.
                while not self._inputs.empty() or (
                    len(self._queue) == 0 and len(self._stack) == 0
                ):
                    try:
                        inp = self._inputs.get(timeout=0.2)
                    except queue.Empty:
                        self._is_idle = True
                        continue
                    task_info, push_to_queue = inp
                    if push_to_queue:
                        self._queue.append(task_info)
                    else:
                        self._stack.append(task_info)

                # A task is required to run.
                self._is_idle = False

                if self._is_paused:
                    while self._is_paused:
                        time.sleep(0.1)
                    if self._step_mode:
                        self._is_paused = True  # pause after one step

                # queue is prioritized
                if len(self._queue) > 0:
                    taskinfo_to_run = self._queue.pop()
                else:
                    taskinfo_to_run = self._stack.pop()

                task, exception_callback = (
                    taskinfo_to_run.task,
                    taskinfo_to_run.exception_callback,
                )
                if isinstance(task, Iterator):
                    try:
                        self._stack.append(TaskInfo(task, exception_callback))
                        next(task)
                    except StopIteration:
                        self._stack.pop()
                    except Exception as e:
                        on_exception(e, exception_callback)
                else:
                    try:
                        ret = task()
                    except Exception as e:
                        on_exception(e, exception_callback)
                    else:
                        # if ret is a generator, push it to stack
                        if isinstance(ret, Iterator):
                            self._stack.append(TaskInfo(iter(ret), exception_callback))

            except RunnerInterrupt:
                logger.info("Runner interrupted")
            except KeyboardInterrupt:
                signal.signal(
                    RUNNER_INTERRUPT_SIGNAL, signal.SIG_DFL
                )  # restore default signal handler when runner exits
                logger.info("Keyboard interrupt")
                raise
            except Exception as e:
                self.clear_tasks()
                orig_print("Runner error", e)

    def pause(self):
        self._is_paused = True
        self._step_mode = False

    def resume(self):
        self._is_paused = False
        self._step_mode = False

    def step(self):
        self._is_paused = False  # will then be immediately set to True
        self._step_mode = True

    def is_paused(self):
        return self._is_paused

    def is_idle(self):
        return self._is_idle
