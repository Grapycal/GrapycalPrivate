import grapycal.utils.logging
import logging
grapycal.utils.logging.setup_logging()
logger = logging.getLogger("workspace")

import os
import threading
import asyncio
import signal
import importlib.metadata
from dacite import from_dict
from typing import Any, Dict
import objectsync
from objectsync.sobject import SObjectSerialized

''' Import utils from grapycal '''
import grapycal
from grapycal.core.slash_command import SlashCommandManager
from grapycal.extension.extension import CommandCtx
from grapycal.extension.extensionManager import ExtensionManager
from grapycal.extension.utils import Clock
from grapycal.utils.httpResource import HttpResource
from grapycal.utils.io import file_exists, read_workspace, write_workspace
from grapycal.core import stdout_helper, running_module
from grapycal.core.background_runner import BackgroundRunner
from grapycal.stores import main_store

''' import all sobject types to register them to the objectsync server '''
from grapycal.sobjects.fileView import LocalFileView, RemoteFileView
from grapycal.sobjects.settings import Settings
from grapycal.sobjects.controls import ButtonControl, ImageControl, LinePlotControl, NullControl, OptionControl, TextControl, ThreeControl
from grapycal.sobjects.editor import Editor
from grapycal.sobjects.workspaceObject import WebcamStream, WorkspaceObject
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.port import InputPort, OutputPort
from grapycal.sobjects.sidebar import Sidebar
from grapycal.sobjects.node import Node

class ClientMsgTypes:
    '''
    Used to specify the type of message to send to the client. 
    Status messages are displayed in the status bar,
    while notifications are displayed as a popup.
    '''
    STATUS = "status"
    NOTIFICATION = "notification"
    BOTH = "both"


class Workspace:
    '''
    This is the core class of a Grapycal workspace.

    To run a Grapycal workspace:

    ```python
    workspace = Workspace(port=8765, host="localhost", path="workspace.grapycal", workspace_id=0)
    workspace.run()
    ```
    '''
    def __init__(self, port, host, path, workspace_id) -> None:
        self.path = path
        self.port = port
        self.host = host

        self.workspace_id = workspace_id 
        '''used for exit message file'''

        self.grapycal_id_count = 0
        self.is_running = False

        self.running_module = running_module
        '''The module that the user's code runs in.'''

        self._objectsync = objectsync.Server(port, host)
        ''' Grapycal uses objectsync to store stateful objects and communicate with the frontend.'''

        # utilities
        self._extention_manager = ExtensionManager(self._objectsync)
        self._slash_commands_topic = self._objectsync.create_topic("slash_commands", objectsync.DictTopic)
        self.slash = SlashCommandManager(self._slash_commands_topic)
        stdout_helper.enable_proxy(redirect_error=False)


    def run(self) -> None:
        '''
        The blocking function that make the workspace start functioning. The main thread will run a background_runner 
        that runs the background tasks from nodes.
        A communication thread will be started to handle the communication between the frontend and the backend.
        '''

        # Register all the sobject types to the objectsync server, and link some events to the callbacks.
        self._setup_objectsync()

        # Setup slash commands
        self._setup_slash_commands()

        # Start the communication thread.
        # The thread runs the objectsync server in an asyncio event loop.
        event_loop_set_event = threading.Event()
        threading.Thread(target=self._communication_thread, daemon=True, args=[event_loop_set_event]).start()  # daemon=True until we have a proper exit strategy
        event_loop_set_event.wait()
        
        # The extension manager starts searching for all extensions available.
        self._extention_manager.start()
        
        # The store is a global object that holds all the data and functions that are shared across classes.
        self._setup_store()

        # Make SObject tree present. After this, the workspace is ready to be used. Most of the operations will be done on the tree.
        self._load_or_create_workspace()

        # Setup is done. Hand the thread over to the background runner.
        signal.signal(signal.SIGTERM, lambda sig, frame: self._exit())
        self.is_running = True
        main_store.runner.run() # this is a blocking call

    '''
    Subroutines of run()
    '''
    
    def _setup_objectsync(self):
        # Register all the sobject types to the objectsync server so they can be created dynamically.
        self._objectsync.register(WorkspaceObject)
        self._objectsync.register(Editor)
        self._objectsync.register(Sidebar)
        self._objectsync.register(Settings)
        self._objectsync.register(LocalFileView)
        self._objectsync.register(RemoteFileView)
        self._objectsync.register(InputPort)
        self._objectsync.register(OutputPort)
        self._objectsync.register(Edge)
    
        self._objectsync.register(TextControl)
        self._objectsync.register(ButtonControl)
        self._objectsync.register(ImageControl)
        self._objectsync.register(ThreeControl)
        self._objectsync.register(NullControl)
        self._objectsync.register(OptionControl)
    
        self._objectsync.register(WebcamStream)
        self._objectsync.register(LinePlotControl)
    
        self._objectsync.on_client_connect += self._client_connected
        self._objectsync.on_client_disconnect += self._client_disconnected
    
        # creates the status message topic so client can subscribe to it
        self._objectsync.create_topic(
            f"status_message", objectsync.EventTopic, is_stateful=False
        )
        self._objectsync.create_topic(
            "meta", objectsync.DictTopic, {"workspace name": self.path}
        )
    
        self._objectsync.register_service("exit", self._exit)
        self._objectsync.register_service("interrupt", self._interrupt)
        self._objectsync.register_service("slash_command", lambda name,ctx: self.slash.call(name,CommandCtx(**ctx)))
    
        self._objectsync.on(
            "ctrl+s", lambda: self._save_workspace(self.path), is_stateful=False
        )
        self._objectsync.on(
            "open_workspace", self._open_workspace_callback, is_stateful=False
        )
    

    def _setup_slash_commands(self):
        self.slash.register("save workspace", lambda ctx: self._save_workspace(self.path)) 
    
    def _communication_thread(self, event_loop_set_event: threading.Event):
        asyncio.run(self._async_communication_thread(event_loop_set_event))
    
    async def _async_communication_thread(self, event_loop_set_event: threading.Event):
        main_store.event_loop = asyncio.get_event_loop()
        event_loop_set_event.set()
        try:
            await self._objectsync.serve()
        except OSError as e:
            if e.errno == 10048:
                logger.error(
                    f"Port {self.port} is already in use. Maybe another instance of grapycal is running?"
                )
                main_store.event_loop.stop()
                # send signal to the main thread to exit
                os.kill(os.getpid(), signal.SIGTERM)
            else:
                raise e

    def _setup_store(self):
        """
        Assign members needed for the main_store.
        """
        main_store.node_types = self._objectsync.create_topic('node_types',objectsync.DictTopic,is_stateful=False)
        main_store.clock = Clock(0.1)
        main_store.event_loop.create_task(main_store.clock.run())
        main_store.redirect = stdout_helper.redirect
        main_store.runner = BackgroundRunner()
        main_store.send_message = self._send_message
        main_store.send_message_to_all = self._send_message_to_all
        grapycal.utils.logging.send_client_msg = main_store.send_message_to_all
        main_store.clear_edges = self._clear_edges
        main_store.open_workspace = self._open_workspace_callback
        main_store.data_yaml = HttpResource("https://github.com/Grapycal/grapycal_data/raw/main/data.yaml", dict)
        main_store.next_id = self._next_id
        main_store.vars = self._vars
        main_store.record = self._objectsync.record

    def _load_or_create_workspace(self):
        """
        Load the workspace if it exists, otherwise create a new one.
        """
        if file_exists(self.path):
            logger.info(f"Found existing workspace file {self.path}. Loading.")
            self._load_workspace(self.path)
        else:
            logger.info(
                f"No workspace file found at {self.path}. Creating a new workspace to start with."
            )
            self._initialize_workspace()
        if not file_exists(self.path):
            self._save_workspace(
                self.path
            )

    """
    Saving and loading workspace
    """

    def _initialize_workspace(self) -> None:
        self._workspace_object = self._objectsync.create_object(WorkspaceObject, parent_id="root")
        try:
            self._extention_manager.import_extension("grapycal_builtin")
        except ModuleNotFoundError:
            pass

    def _save_workspace(self, path: str) -> None:
        workspace_serialized = self._workspace_object.serialize()

        metadata = {
            "version": grapycal.__version__,
            "extensions": self._extention_manager.get_extensions_info(),
        }
        data = {
            "extensions": self._extention_manager.get_extention_names(),
            "client_id_count": self._objectsync.get_client_id_count(),
            "id_count": self._objectsync.get_id_count(),
            "grapycal_id_count": self.grapycal_id_count,
            "workspace_serialized": workspace_serialized.to_dict(),
        }
        file_size = write_workspace(path, metadata, data, compress=True)
        node_count = len(
            main_store.main_editor.top_down_search(type=Node)
        )
        edge_count = len(
            main_store.main_editor.top_down_search(type=Edge)
        )
        logger.info(
            f"Workspace saved to {path}. Node count: {node_count}. Edge count: {edge_count}. File size: {file_size//1024} KB."
        )
        self._send_message_to_all(
            f"Workspace saved to {path}. Node count: {node_count}. Edge count: {edge_count}. File size: {file_size//1024} KB."
        )

    def _load_workspace(self, path: str) -> None:
        version, metadata, data = read_workspace(path)

        self._check_grapycal_version(version)
        self._check_extensions_version(metadata["extensions"])

        self._objectsync.set_client_id_count(data["client_id_count"])
        self._objectsync.set_id_count(data["id_count"])
        self.grapycal_id_count = data["grapycal_id_count"]
        workspace_serialized = from_dict(
            SObjectSerialized, data["workspace_serialized"]
        )

        for extension_name in data["extensions"]:
            self._extention_manager.import_extension(extension_name, create_nodes=False)

        self._workspace_object = self._objectsync.create_object(
            WorkspaceObject,
            parent_id="root",
            old=workspace_serialized,
            id=workspace_serialized.id,
        )

        for extension_name in data["extensions"]:
            self._extention_manager.create_preview_nodes(extension_name)
            self._extention_manager._instantiate_singletons(extension_name)

        self._objectsync.clear_history_inclusive()

    def _check_grapycal_version(self, version: str):
        # check if the workspace version is compatible with the current version
        workspace_version_tuple = tuple(map(int, version.split(".")))
        current_version_tuple = tuple(map(int, grapycal.__version__.split(".")))
        if current_version_tuple < workspace_version_tuple:
            logger.warning(
                f"Attempting to downgrade workspace from version {version} to {grapycal.__version__}. This may cause errors."
            )

    def _check_extensions_version(self, extensions_info):
        # check if all extensions version are compatible with the current version
        for extension_info in extensions_info:
            extension_version_tuple = tuple(
                map(int, extension_info["version"].split("."))
            )
            try:
                current_version_tuple = tuple(
                    map(
                        int,
                        importlib.metadata.version(extension_info["name"]).split("."),
                    )
                )
            except importlib.metadata.PackageNotFoundError:
                continue  # ignore extensions that are not installed
            if current_version_tuple < extension_version_tuple:
                logger.warning(
                    f'Attempting to downgrade extension {extension_info["name"]} from version {extension_info["version"]} to {importlib.metadata.version(extension_info["name"])}. This may cause errors.'
                )

    def _open_workspace_callback(self, path, no_exist_ok=False):
        if not no_exist_ok:
            if not os.path.exists(path):
                raise Exception(f"File {path} does not exist")
        if not path.endswith(".grapycal"):
            raise Exception(f"File {path} does not end with .grapycal")

        logger.info(f"Opening workspace {path}...")
        self._send_message_to_all(f"Opening workspace {path}...")

        exit_message_file = f"grapycal_exit_message_{self.workspace_id}"
        with open(exit_message_file, "w") as f:
            f.write(f"open {path}")
        self._exit()

    '''
    Utility functions
    '''
    def _send_message_to_all(self, message, type=ClientMsgTypes.NOTIFICATION):
        if not self.is_running:
            return
        if type == ClientMsgTypes.BOTH:
            self._send_message_to_all(message, ClientMsgTypes.NOTIFICATION)
            self._send_message_to_all(message, ClientMsgTypes.STATUS)
    
        self._objectsync.emit("status_message", message=message, type=type)
    
    def _send_message(self, message, client_id=None, type=ClientMsgTypes.NOTIFICATION):
        if not self.is_running:
            return
        if type == ClientMsgTypes.BOTH:
            self._send_message(message, ClientMsgTypes.NOTIFICATION)
            self._send_message(message, ClientMsgTypes.STATUS)
        if client_id is None:
            client_id = self._objectsync.get_action_source()
        self._objectsync.emit(f"status_message_{client_id}", message=message, type=type)
    
    
    def _next_id(self):
        self.grapycal_id_count += 1
        return self.grapycal_id_count
    
    def _clear_edges(self):
        edges = self._workspace_object.top_down_search(type=Edge)
        for edge in edges:
            edge.clear()
    
    def _vars(self) -> Dict[str, Any]:
        return self.running_module.__dict__

    '''
    Callbacks
    '''
    def _exit(self):
        main_store.runner.exit()
    
    def _interrupt(self):
        main_store.runner.interrupt()
        main_store.runner.clear_tasks()
    
    def _client_connected(self, client_id):
        self._objectsync.create_topic(
            f"status_message_{client_id}", objectsync.EventTopic
        )
    
    def _client_disconnected(self, client_id):
        try:
            self._objectsync.remove_topic(f"status_message_{client_id}")
        except:
            pass  # topic may have not been created successfully.


import argparse
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--path", type=str, default="workspace.grapycal")
    parser.add_argument("--workspace_id", type=int, default=0)
    args = parser.parse_args()

    workspace = Workspace(args.port, args.host, args.path, args.workspace_id)
    workspace.run()
