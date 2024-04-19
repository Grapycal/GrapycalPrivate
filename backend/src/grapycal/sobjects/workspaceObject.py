import logging

from grapycal.stores import main_store

logger = logging.getLogger("WORKSPACE")
from typing import Any, Dict, Self
from grapycal.sobjects.edge import Edge
from grapycal.sobjects.editor import Editor
from grapycal.sobjects.fileView import FileView, LocalFileView, RemoteFileView
from grapycal.sobjects.node import Node
from grapycal.sobjects.nodeLibrary import NodeLibrary
from grapycal.sobjects.settings import Settings
from objectsync import (
    SObject,
    ObjTopic,
    SObjectSerialized,
    StringTopic,
    IntTopic,
    Topic,
    WrappedTopic,
)


class WorkspaceObject(SObject):
    frontend_type = "Workspace"

    def build(self, old: SObjectSerialized | None = None):
        if old is None:
            self.settings = self.add_child(Settings)
            self.webcam = self.add_child(WebcamStream)
            self.node_library = self.add_child(NodeLibrary)
        else:
            self.settings = self.add_child(Settings, old=old.get_child("settings"))
            self.webcam = self.add_child(WebcamStream, old=old.get_child("webcam"))

            #BACKWARD COMPATIBILITY: v0.11.3 and below, node_library was called sidebar
            if old.has_child("node_library"):
                old_node_library = old.get_child("node_library")
            else:
                old_node_library = old.get_child("sidebar")

            self.node_library = self.add_child(NodeLibrary, old=old_node_library)

        main_store.settings = self.settings
        main_store.webcam = self.webcam
        main_store.node_library = self.node_library

        if old is None:
            self.main_editor = self.add_child(Editor)
        else:
            self.main_editor = self.add_child(Editor, old=old.get_child("main_editor") )
        
        main_store.main_editor = self.main_editor
        
        # Add local file view and remote file view
        self.file_view = self.add_child(LocalFileView, name="Local Files 💻")

        async def add_examples_file_view():
            if not await main_store.data_yaml.is_avaliable():
                logger.info("Cannot get example files from GitHub.")
                return  # no internet connection
            data_yaml = await main_store.data_yaml.get()

            self.add_child(
                RemoteFileView, url=data_yaml["examples_url"], name="Examples💡"
            )
            self._server.clear_history()

        main_store.event_loop.create_task(add_examples_file_view())

        # read by frontend
        self.add_attribute("main_editor", ObjTopic).set(self.main_editor)

class WebcamStream(SObject):
    frontend_type = "WebcamStream"

    def build(self, old: SObjectSerialized | None = None):
        self.image = self.add_attribute("image", StringTopic, is_stateful=False)
        self.source_client = self.add_attribute(
            "source_client", IntTopic, -1, is_stateful=False
        )

    def init(self):
        self.source_client.set(-1)
