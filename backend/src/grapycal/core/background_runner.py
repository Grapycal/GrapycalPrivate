import logging

logger = logging.getLogger(__name__)

from collections import deque
from contextlib import contextmanager
from queue import Queue
import queue
from typing import Callable, Iterator, Tuple
import signal
from .stdout_helper import orig_print


class TaskInfo:
    def __init__(self, task: Callable | Iterator, exception_callback: Callable[[Exception], None] | None = None):
        self.task = task
        self.exception_callback = exception_callback


def on_exception(e: Exception, exception_callback: Callable[[Exception], None] | None = None):
    if exception_callback is None:
        orig_print('No exception callback', e)
    else:
        exception_callback(e)


class BackgroundRunner:
    def __init__(self):
        self._inputs: Queue[Tuple[TaskInfo, bool]] = Queue()
        self._queue: deque[TaskInfo] = deque()
        self._stack: deque[TaskInfo] = deque()
        self._exit_flag = False

    def push(self, task: Callable, to_queue: bool = True,
             exception_callback: Callable[[Exception], None] | None = None):
        self._inputs.put((TaskInfo(task, exception_callback), to_queue))

    def push_to_queue(self, task: Callable, exception_callback: Callable[[Exception], None] | None = None):
        self._inputs.put((TaskInfo(task, exception_callback), True))

    def push_to_stack(self, task: Callable, exception_callback: Callable[[Exception], None] | None = None):
        self._inputs.put((TaskInfo(task, exception_callback), False))

    def interrupt(self):
        signal.raise_signal(signal.SIGINT)

    def clear_tasks(self):
        self._queue.clear()
        self._stack.clear()

    def exit(self):
        self._exit_flag = True
        self.interrupt()

    @contextmanager
    def no_interrupt(self):
        def handler(signum, frame):
            logger.info("Cannot interrupt current task")

        original_sigint_handler = signal.getsignal(signal.SIGINT)
        try:
            signal.signal(signal.SIGINT, handler)
            yield
        finally:
            signal.signal(signal.SIGINT, original_sigint_handler)

    def run(self):
        while True:
            if self._exit_flag:
                break
            try:
                # Queue.get() blocks signal.
                while not self._inputs.empty() or (len(self._queue) == 0 and len(self._stack) == 0):
                    try:
                        inp = self._inputs.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    task_info, push_to_queue = inp
                    if push_to_queue:
                        self._queue.append(task_info)
                    else:
                        self._stack.append(task_info)

                # queue is prioritized
                if len(self._queue) > 0:
                    taskinfo_to_run = self._queue.pop()
                else:
                    taskinfo_to_run = self._stack.pop()

                task, exception_callback = taskinfo_to_run.task, taskinfo_to_run.exception_callback
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
                    # if ret is a generator, push it to stack
                    if isinstance(ret, Iterator):
                        self._stack.append(TaskInfo(iter(ret), exception_callback))

            except KeyboardInterrupt as e:
                logger.info("Runner interrupted")
            except Exception as e:
                self.clear_tasks()
                orig_print('Runner error', e)
