import asyncio
import importlib.metadata
import logging
import os
import random
import signal
from typing import Any, Dict

# Import utils from grapycal
import grapycal
from grapycal.sobjects.controlPanel import ControlPanel
from grapycal.sobjects.controls.floatControl import FloatControl
from grapycal.sobjects.controls.intControl import IntControl
import grapycal.utils.logging
from grapycal.utils.misc import SemVer
from grapycal.utils.os_stat import OSStat
import objectsync
from dacite import from_dict
from grapycal.core import running_module, stdout_helper
from grapycal.core.background_runner import BackgroundRunner

# import all sobject types to register them to the objectsync server
from grapycal.core.client_msg_types import ClientMsgTypes
from grapycal.core.slash_command import SlashCommandManager
from grapycal.core.strategies import OpenAnotherWorkspaceStrategy
from grapycal.extension.extension import CommandCtx
from grapycal.extension.extensionManager import ExtensionManager
from grapycal.extension.utils import Clock
from grapycal.sobjects.controls import (
    ButtonControl,
    CodeControl,
    ImageControl,
    LinePlotControl,
    NullControl,
    OptionControl,
    TextControl,
    ThreeControl,
)
from grapycal.sobjects.controls.keyboardControl import KeyboardControl
from grapycal.sobjects.controls.sliderControl import SliderControl
from grapycal.sobjects.controls.toggleControl import ToggleControl
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.editor import Editor
from grapycal.sobjects.fileView import LocalFileView, RemoteFileView
from grapycal.sobjects.node import Node
from grapycal.sobjects.nodeLibrary import NodeLibrary
from grapycal.sobjects.port import InputPort, OutputPort
from grapycal.sobjects.settings import Settings
from grapycal.sobjects.workspaceObject import WebcamStream, WorkspaceObject
from grapycal.stores import main_store
from grapycal.utils.httpResource import HttpResource
from grapycal.utils.io import file_exists, read_workspace, write_workspace
from objectsync.sobject import SObjectSerialized

grapycal.utils.logging.setup_logging()
logger = logging.getLogger("workspace")


class Workspace:
    """
    This is the core class of a Grapycal workspace.

    To run a Grapycal workspace:

    ```python
    workspace = Workspace("workspace.grapycal")
    workspace.run()
    ```
    """

    def __init__(
        self,
        path: str,
        open_another_workspace_strategy: OpenAnotherWorkspaceStrategy | None = None,
    ):
        self.path = path

        self._open_another_workspace_strategy = open_another_workspace_strategy
        """used for exit message file"""

        self.grapycal_id_count = 0
        self.is_running = False

        self.running_module = running_module
        """The module that the user's code runs in."""

        self._objectsync = objectsync.Server()
        """ Grapycal uses objectsync to store stateful objects and communicate with the frontend."""

        # utilities
        self._extention_manager = ExtensionManager(self._objectsync)
        self._slash_commands_topic = self._objectsync.create_topic(
            "slash_commands", objectsync.DictTopic
        )
        self.slash = SlashCommandManager(self._slash_commands_topic)
        self._os_stat = OSStat()
        stdout_helper.enable_proxy(redirect_error=False)

    def run(self, ui_thread_event_loop: asyncio.AbstractEventLoop, run_runner=True):
        """
        The blocking function that make the workspace start functioning. The main thread will run a background_runner
        that runs the background tasks from nodes.
        A communication thread will be started to handle the communication between the frontend and the backend.

        args:
            run_runner: bool
                Set to False if you don't want to run the background runner. This is useful for testing.
        """

        # Register all the sobject types to the objectsync server, and link some events to the callbacks.
        self._setup_objectsync()

        # Setup slash commands
        self._setup_slash_commands()

        # The store is a global object that holds all the data and functions that are shared across classes.
        main_store.event_loop = ui_thread_event_loop
        self._setup_store()

        ui_thread_event_loop.create_task(self.auto_save())
        ui_thread_event_loop.create_task(self._objectsync.serve())

        main_store.clock.add_listener(self._update_os_stat, 2)

        # The extension manager starts searching for all extensions available.
        self._extention_manager.start()

        # Make SObject tree present. After this, the workspace is ready to be used. Most of the operations will be done on the tree.
        self._load_or_create_workspace()

        # ===CHECK_LICENSE=== #

        # Setup is done. Hand the thread over to the background runner.
        if run_runner:
            signal.signal(signal.SIGTERM, lambda sig, frame: self._exit())
            self.is_running = True
            main_store.runner.run()  # this is a blocking call

    """
    Subroutines of run()
    """

    def _setup_objectsync(self):
        # Register all the sobject types to the objectsync server so they can be created dynamically.
        self._objectsync.register(WorkspaceObject)
        self._objectsync.register(Editor)
        self._objectsync.register(NodeLibrary)
        self._objectsync.register(Settings)
        self._objectsync.register(ControlPanel)
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
        self._objectsync.register(KeyboardControl)
        self._objectsync.register(CodeControl)
        self._objectsync.register(SliderControl)
        self._objectsync.register(ToggleControl)
        self._objectsync.register(IntControl)
        self._objectsync.register(FloatControl)

        self._objectsync.register(WebcamStream)
        self._objectsync.register(LinePlotControl)

        self._objectsync.on_client_connect += self._client_connected
        self._objectsync.on_client_disconnect += self._client_disconnected

        # creates the status message topic so client can subscribe to it
        self._objectsync.create_topic(
            "status_message", objectsync.EventTopic, is_stateful=False
        )
        self._objectsync.create_topic(
            "meta", objectsync.DictTopic, {"workspace name": self.path}
        )
        self._os_stat_topic = self._objectsync.create_topic(
            "os_stat", objectsync.DictTopic, self._os_stat.get_os_stat()
        )

        self._objectsync.register_service("exit", self._exit)
        self._objectsync.register_service("interrupt", self._interrupt)
        self._objectsync.register_service(
            "slash_command",
            lambda name, ctx, args: self.slash.call(name, CommandCtx(**ctx), args),
        )
        self._objectsync.register_service(
            "ctrl+s", lambda: self._save_workspace(self.path)
        )
        self._objectsync.register_service(
            "open_workspace", self._open_workspace_callback
        )

    def _setup_slash_commands(self):
        self.slash.register(
            "save workspace", lambda ctx: self._save_workspace(self.path)
        )

    def _setup_store(self):
        """
        Assign members needed for the main_store.
        """
        main_store.node_types = self._objectsync.create_topic(
            "node_types", objectsync.DictTopic, is_stateful=False
        )
        main_store.clock = Clock(0.01)
        main_store.event_loop.create_task(main_store.clock.run())
        main_store.redirect = stdout_helper.redirect
        main_store.runner = BackgroundRunner()
        main_store.send_message = self._send_message
        main_store.send_message_to_all = self._send_message_to_all
        grapycal.utils.logging.send_client_msg = main_store.send_message_to_all
        main_store.clear_edges_and_tasks = self._clear_edges_and_tasks
        main_store.open_workspace = self._open_workspace_callback
        main_store.data_yaml = HttpResource(
            "https://github.com/Grapycal/grapycal_data/raw/main/data.yaml", dict
        )
        main_store.next_id = self._next_id
        main_store.vars = self._vars
        main_store.record = self._objectsync.record
        main_store.slash = self.slash
        main_store.session_id = random.randint(0, 1000000000)

        # runner control. It's put here because it needs main_store.runner
        # the play is handled by controlPanel.py
        self._objectsync.register_service("pause", main_store.runner.pause)
        self._objectsync.register_service("resume", main_store.runner.resume)
        self._objectsync.register_service("step", main_store.runner.step)

    def _load_or_create_workspace(self):
        """
        Load the workspace if it exists, otherwise create a new one.
        """
        if file_exists(self.path):
            logger.info(f"Found existing workspace file {self.path}. Loading.")
            try:
                self._load_workspace(self.path)
            except Exception:
                logger.error("Failed to load workspace.")
                raise
        else:
            logger.info(
                f"No workspace file found at {self.path}. Creating a new workspace to start with."
            )
            self._initialize_workspace()
        if not file_exists(self.path):
            self._save_workspace(self.path)

    """
    Saving and loading workspace
    """

    def _initialize_workspace(self) -> None:
        self._workspace_object = self._objectsync.create_object(
            WorkspaceObject, parent_id="root"
        )
        # ===CHECK_LICENSE=== #
        try:
            self._extention_manager.import_extension("grapycal_builtin")
        except ModuleNotFoundError:
            pass

    def _save_workspace(self, path: str, send_message=True) -> None:
        with self._objectsync.record():  # lock the state of the workspace
            node_count = len(main_store.main_editor.top_down_search(type=Node))
            edge_count = len(main_store.main_editor.top_down_search(type=Edge))

            # % enable_for_demo
            # if node_count > 150:
            #     logger.warning(
            #         f"Sorry, cannot save workspace with more than 150 nodes in demo edition. {node_count} nodes found. Please remove some nodes and try again."
            #     )
            #     if send_message:
            #         self._send_message_to_all(
            #             f"Sorry, cannot save workspace with more than 150 nodes in demo edition. {node_count} nodes found. Please remove some nodes and try again."
            #         )
            #     return
            # else:
            #     workspace_serialized = self._workspace_object.serialize()
            # % end_enable_for_demo

            # % disable_for_demo
            workspace_serialized = self._workspace_object.serialize()
            # % end_disable_for_demo

        metadata = {
            "version": grapycal.__version__,
            "extensions": self._extention_manager.get_extensions_info(),
        }

        # % enable_for_demo
        # e = self._extention_manager.get_extention_names()
        # a = 64
        # b = 58
        # if (len(e) * len(e) * len(e) > a) or not str(((b * b + a) ^ 1545) / 53)[
        #     5:12
        # ] == "8679245":
        #     logger.warning(
        #         f"Sorry, cannot save workspace with more than 4 extensions in demo edition. {len(e)} extensions found. Please unimport some extensions and try again."
        #     )
        #     if send_message:
        #         self._send_message_to_all(
        #             f"Sorry, cannot save workspace with more than 4 extensions in demo edition. {len(e)} extensions found. Please unimport some extensions and try again."
        #         )
        #     return
        # else:
        #     if len([64,64,1545,2,a,b]*2) != a-52:
        #         return
        #     data = {
        #         "extensions": self._extention_manager.get_extention_names()[0:4],
        #         "client_id_count": self._objectsync.get_client_id_count(),
        #         "id_count": self._objectsync.get_id_count(),
        #         "grapycal_id_count": self.grapycal_id_count,
        #         "workspace_serialized": workspace_serialized.to_dict(),
        #     }
        # % end_enable_for_demo

        # % disable_for_demo
        data = {
            "extensions": self._extention_manager.get_extention_names(),
            "client_id_count": self._objectsync.get_client_id_count(),
            "id_count": self._objectsync.get_id_count(),
            "grapycal_id_count": self.grapycal_id_count,
            "workspace_serialized": workspace_serialized.to_dict(),
        }
        # % end_disable_for_demo

        file_size = write_workspace(path, metadata, data, compress=True)
        logger.info(
            f"Workspace saved to {path}. {node_count} nodes, {edge_count} edges, {file_size // 1024} KB."
        )
        if send_message:
            self._send_message_to_all(
                f"Workspace saved to {path}. {node_count} nodes, {edge_count} edges, {file_size // 1024} KB."
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
        workspace_version = SemVer(version)
        current_version = SemVer(grapycal.__version__)
        if current_version < workspace_version:
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

        self._open_another_workspace_strategy.open(path)

        self._exit()

    """
    Utility functions
    """

    def _send_message_to_all(self, message, type=ClientMsgTypes.NOTIFICATION):
        if not self.is_running:
            return
        if type == ClientMsgTypes.BOTH:
            self._send_message_to_all(message, ClientMsgTypes.NOTIFICATION)
            self._send_message_to_all(message, ClientMsgTypes.STATUS)

        self._objectsync.emit("status_message", message=message, type=type.value)

    def _send_message(self, message, client_id=None, type=ClientMsgTypes.NOTIFICATION):
        if not self.is_running:
            return
        if type == ClientMsgTypes.BOTH:
            self._send_message(message, ClientMsgTypes.NOTIFICATION)
            self._send_message(message, ClientMsgTypes.STATUS)
        if client_id is None:
            client_id = self._objectsync.get_action_source()
        self._objectsync.emit(
            f"status_message_{client_id}", message=message, type=type.value
        )

    def _next_id(self):
        self.grapycal_id_count += 1
        return self.grapycal_id_count

    def _clear_edges_and_tasks(self):
        edges = self._workspace_object.top_down_search(type=Edge)
        for edge in edges:
            edge.clear()
        main_store.runner.clear_tasks()

    def _vars(self) -> Dict[str, Any]:
        return self.running_module.__dict__

    """
    Callbacks
    """

    def _exit(self):
        main_store.runner.exit()

    def _interrupt(self):
        main_store.runner.interrupt()
        self._clear_edges_and_tasks()

    def _client_connected(self, client_id):
        self._objectsync.create_topic(
            f"status_message_{client_id}", objectsync.EventTopic
        )

    def _client_disconnected(self, client_id):
        try:
            self._objectsync.remove_topic(f"status_message_{client_id}")
        except KeyError:
            pass  # topic may have not been created successfully.

    async def auto_save(self):
        while True:
            await asyncio.sleep(60)
            self._save_workspace(self.path, send_message=False)

    def _update_os_stat(self):
        self._os_stat_topic.set(self._os_stat.get_os_stat())
