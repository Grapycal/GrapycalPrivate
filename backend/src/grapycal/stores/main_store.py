
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

if TYPE_CHECKING:
    from contextlib import _GeneratorContextManager
    from grapycal.extension.utils import Clock
    from objectsync import DictTopic
    from grapycal.core.background_runner import BackgroundRunner
    from grapycal.sobjects.editor import Editor
    from grapycal.sobjects.settings import Settings
    from grapycal.sobjects.workspaceObject import WebcamStream
    from grapycal.utils.httpResource import HttpResource
    import asyncio

class MainStore:
    def __init__(self):

        # set by Workspace
        self.node_types: DictTopic
        self.clock: Clock
        self.event_loop: asyncio.AbstractEventLoop
        self.redirect: Callable[[Any],_GeneratorContextManager[None]]
        self.runner: BackgroundRunner
        self.send_message: Callable[[str,str],None]
        self.send_message_to_all: Callable[[str],None]
        self.clear_edges: Callable[[],None]
        self.data_yaml: HttpResource
        self.next_id: Callable[[],int]
        self.vars: Callable[[],Dict[str,Any]]

        # set by workspaceObject

        self.main_editor: Editor
        self.settings: Settings
        self.webcam: WebcamStream
    
    def open_workspace(self, path, no_exist_ok=False):
        raise NotImplementedError()

main_store = MainStore()
__all__ = ['main_store']
