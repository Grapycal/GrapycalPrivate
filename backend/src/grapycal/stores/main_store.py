
from typing import TYPE_CHECKING, Any, Callable, Dict, Protocol

from grapycal.core.slash_command import SlashCommandManager

if TYPE_CHECKING:
    import asyncio
    from contextlib import _GeneratorContextManager

    from objectsync import DictTopic

    from grapycal.core.background_runner import BackgroundRunner
    from grapycal.core.workspace import ClientMsgTypes
    from grapycal.extension.utils import Clock
    from grapycal.sobjects.editor import Editor
    from grapycal.sobjects.nodeLibrary import NodeLibrary
    from grapycal.sobjects.settings import Settings
    from grapycal.sobjects.workspaceObject import WebcamStream
    from grapycal.utils.httpResource import HttpResource

    class SendMessageProtocol(Protocol):
        def __call__(self, message: str, client_id: int, type: ClientMsgTypes = ...) -> None:
            ...

    class SendMessageToAllProtocol(Protocol):
        def __call__(self, message: str, type: ClientMsgTypes = ...) -> None:
            ...

class MainStore:
    def __init__(self):

        # set by Workspace
        self.node_types: DictTopic
        self.clock: Clock
        self.event_loop: asyncio.AbstractEventLoop
        self.redirect: Callable[[Any],_GeneratorContextManager[None]]
        self.runner: BackgroundRunner
        self.send_message: SendMessageProtocol
        self.send_message_to_all: SendMessageToAllProtocol
        self.clear_edges_and_tasks: Callable[[],None]
        self.data_yaml: HttpResource
        self.next_id: Callable[[],int]
        self.vars: Callable[[],Dict[str,Any]]
        self.record: Callable[[],_GeneratorContextManager[None]]
        self.slash: SlashCommandManager

        # set by workspaceObject

        self.main_editor: Editor
        self.settings: Settings
        self.webcam: WebcamStream
        self.node_library: NodeLibrary
    
    # set by Workspace
    def open_workspace(self, path, no_exist_ok=False):
        raise NotImplementedError()

main_store = MainStore()
__all__ = ['main_store']
