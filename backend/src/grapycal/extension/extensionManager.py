import asyncio
import logging
import pkgutil
import subprocess

from grapycal.extension.utils import (
    get_all_dependents,
    get_extension_info,
    list_to_dict,
    snap_node,
)
from grapycal.stores import main_store

logger = logging.getLogger(__name__)

from typing import TYPE_CHECKING, Dict, List

import objectsync

from grapycal.extension.extension import CommandCtx, Extension, get_extension
from grapycal.sobjects.node import Node
from grapycal.sobjects.port import Port

if TYPE_CHECKING:
    pass


class ExtensionManager:
    def __init__(self, objectsync_server: objectsync.Server) -> None:
        self._objectsync = objectsync_server
        self._extensions: Dict[str, Extension] = {}

        # Use this topic to inform the client about the extensions
        self._imported_extensions_topic = self._objectsync.create_topic(
            "imported_extensions", objectsync.DictTopic, is_stateful=False
        )
        self._avaliable_extensions_topic = self._objectsync.create_topic(
            "avaliable_extensions", objectsync.DictTopic, is_stateful=False
        )
        self._not_installed_extensions_topic = self._objectsync.create_topic(
            "not_installed_extensions", objectsync.DictTopic, is_stateful=False
        )
        self._objectsync.register_service("import_extension", self.import_extension)
        self._objectsync.register_service("unimport_extension", self.unimport_extension)
        self._objectsync.register_service("update_extension", self.update_extension)
        self._objectsync.register_service(
            "refresh_extensions", self._update_available_extensions_topic
        )
        self._objectsync.register_service("install_extension", self._install_extension)

    def start(self) -> None:
        """
        Called after the event loop is started.
        """
        self._update_available_extensions_topic()

    def import_extension(
        self, extension_name: str, create_nodes=True, log=True
    ) -> None:
        """
        Import an extension by name. Its dependencies will be imported recursively.
        """
        if extension_name in self._extensions:
            return
        self._import_extension_raw(extension_name, create_nodes, log)
        target_ext = self._extensions[extension_name]

        dependencies = target_ext.dependencies
        for dependency in dependencies:
            logger.info(f"Found dependency {dependency} <- {extension_name}")
            self.import_extension(dependency, create_nodes, log)  # recursive import

    def _import_extension_raw(
        self, extension_name: str, create_nodes=True, log=True
    ) -> None:
        extension = self._load_extension(extension_name)
        main_store.set_stores(extension.provide_stores())
        if create_nodes:
            try:
                self.create_preview_nodes(extension_name)
            except Exception:
                self._unload_extension(extension_name)  # TODO: prevent unloading fail
                raise
            self._instantiate_singletons(extension_name)
        self._update_available_extensions_topic()
        main_store.slash.register(
            f"reload: {extension_name}",
            lambda _: self.update_extension(extension_name),
            source=extension_name,
        )
        main_store.slash.register(
            f"unimport: {extension_name}",
            lambda _: self.unimport_extension(extension_name),
            source=extension_name,
        )
        if log:
            logger.info(f"Imported extension {extension_name}")
            main_store.send_message_to_all(f"Imported extension {extension_name}")
        self._objectsync.clear_history_inclusive()

    def update_extension(self, extension_name: str) -> None:
        old_exts: list[Extension] = get_all_dependents(
            self._extensions[extension_name], list(self._extensions.values())
        )
        new_exts: list[Extension] = []
        for ext in old_exts:
            new_exts.append(
                get_extension(
                    ext.name,
                    set(self._objectsync.get_all_node_types().values())
                    - set(ext.node_types_d.values()),
                )
            )

        old_node_types = set()
        for ext in old_exts:
            old_node_types.update(ext.node_types_d.keys())

        new_node_types = set()
        for ext in new_exts:
            new_node_types.update(ext.node_types_d.keys())

        # Get diff between old and new version
        removed_node_types = old_node_types - new_node_types
        added_node_types = new_node_types - old_node_types
        changed_node_types = old_node_types & new_node_types

        logger.info(
            f"Updating extension {[ext.name for ext in old_exts]}: removed {removed_node_types}, added {added_node_types}"
        )

        # Find nodes of changed types and serialize them
        def get_node_of_types(types: set[str]) -> List[Node]:
            def hit(node: objectsync.SObject) -> bool:
                # Only update nodess...
                if not isinstance(node, Node):
                    return False
                if node.is_preview.get():
                    return False

                # of the changed types.
                # Node type name format: grapycal_packagename.node_type_name
                return node.get_type_name() in types

            return main_store.main_editor.top_down_search(
                accept=hit, stop=hit, type=Node
            )

        nodes_to_update = get_node_of_types(changed_node_types)
        nodes_to_remove = get_node_of_types(removed_node_types)

        nodes_to_recover: List[objectsync.sobject.SObjectSerialized] = []
        edges_to_recover: List[objectsync.sobject.SObjectSerialized] = []

        # serialize nodes and edges to recover
        for node in nodes_to_update:
            nodes_to_recover.append(node.serialize())
            ports: List[Port] = node.in_ports.get() + node.out_ports.get()  # type: ignore
            for port in ports:
                for edge in port.edges.copy():
                    edges_to_recover.append(edge.serialize())
                    self._objectsync.destroy_object(edge.get_id())

        # destroy nodes and edges to be removed
        for node in nodes_to_remove:
            ports: List[Port] = node.in_ports.get() + node.out_ports.get()  # type: ignore
            for port in ports:
                for edge in port.edges.copy():
                    self._objectsync.destroy_object(edge.get_id())

        """
        Now, the old nodes, ports and edges are destroyed. Their information is stored in nodes_to_recover and edges_to_recover.
        """

        # Unimport old version

        for old_version in reversed(
            old_exts
        ):  # Unimport dependents first, then dependencies
            self._destroy_nodes(old_version.name)
            self.unimport_extension(old_version.name, log=False)

        for new_version in new_exts:
            self.import_extension(new_version.name, create_nodes=False, log=False)

        main_store.main_editor.restore(nodes_to_recover, edges_to_recover)

        for new_version in new_exts:
            self.create_preview_nodes(new_version.name)
            self._instantiate_singletons(new_version.name)

        self._update_available_extensions_topic()

        main_store.send_message_to_all(
            f"Reloaded extension {[ext.name for ext in old_exts]}"
        )
        self._objectsync.clear_history_inclusive()

    def unimport_extension(self, extension_name: str, log=True) -> None:
        # dependents need to be unloaded first
        for dependent in get_all_dependents(
            self._extensions[extension_name],
            list(self._extensions.values()),
            include_target=False,
        ):
            if dependent in self._extensions.values():
                logger.warning(
                    f"Please unimport dependent extension {dependent.name} before unimport {extension_name}"
                )
                return

        self._check_extension_not_used(extension_name)
        self._destroy_nodes(extension_name)
        self._unload_extension(extension_name)
        self._update_available_extensions_topic()
        main_store.slash.unregister_source(extension_name)
        if log:
            logger.info(f"Unimported extension {extension_name}")
            main_store.send_message_to_all(f"Unimported extension {extension_name}")
        self._objectsync.clear_history_inclusive()

    def _instantiate_singletons(self, extension_name: str) -> None:
        """
        For each singleton node type, create an instance if there is none.
        """
        extension = self._extensions[extension_name]
        for node_type_name, node_type in extension.singletonNodeTypes.items():
            if node_type._auto_instantiate and not hasattr(node_type, "instance"):
                main_store.main_editor.create_node(
                    node_type, translation="9999,9999", is_new=True
                )

    def _update_available_extensions_topic(self) -> None:
        main_store.event_loop.create_task(
            self._update_available_extensions_topic_async()
        )

    async def _update_available_extensions_topic_async(self) -> None:
        """
        This function is async because it sends requests to get package metadata.
        """
        available_extensions = self._scan_available_extensions()
        self._avaliable_extensions_topic.set(list_to_dict(available_extensions, "name"))
        main_store.slash.unregister_source("import_extension")
        for extension in available_extensions:
            extension_name = extension["name"] + ""
            main_store.slash.register(
                f"import: {extension_name}",
                lambda _, n=extension_name: self.import_extension(n),
                source="import_extension",
            )

        # The functionality of downloading extensions from the internet is disabled for now.

        # not_installed_extensions = await get_remote_extensions()
        # not_installed_extensions = [
        #     info
        #     for info in not_installed_extensions
        #     if (
        #         info["name"] not in self._avaliable_extensions_topic
        #         and info["name"] not in self._imported_extensions_topic
        #     )
        # ]
        # self._not_installed_extensions_topic.set(
        #     list_to_dict(not_installed_extensions, "name")
        # )

    def _scan_available_extensions(self) -> list[dict]:
        """
        Returns a list of available extensions that is importable but not imported yet.
        """
        available_extensions = []
        for pkg in pkgutil.iter_modules():
            if pkg.name.startswith("grapycal_") and pkg.name != "grapycal":
                if pkg.name not in self._extensions:
                    # find pyproject.toml and get package version
                    available_extensions.append(get_extension_info(pkg.name))

        return available_extensions

    async def _check_extension_compatible(self, extension_name: str):
        # dry run the installation and get its output
        out = await asyncio.create_subprocess_exec(
            "pip", "install", extension_name, "--dry-run", stdout=subprocess.PIPE
        )
        out = await out.stdout.read()
        out = out.decode("utf-8")
        # check if the line begin with "Would install" contains "grapycal"
        package_regex = r"([^\s]*)-(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
        for line in out.split("\n"):
            if line.startswith("Would install"):
                # use regex to get the package name
                import re

                for match in re.findall(package_regex, line):
                    if match[0] == "grapycal":
                        # This shows that pip will reinstall grapycal, maybe in a different version.
                        # This is not allowed when the extension is installed from the UI.
                        from importlib.metadata import version

                        cur = version("grapycal")

                        raise Exception(f'Cannot install extension {extension_name}.\n\
                            Current grapycal version:\t{cur}. \n\
                            Required grapycal version:\t{match[1]}.{match[2]}.{match[3]}.\n\
                            Please update grapycal first with "pip install --upgrade grapycal".\n\
                            If grapycal is installed in editable mode, please reinstall grapycal with "pip install -e backend"\
                            ')

    def _install_extension(self, extension_name: str) -> None:
        main_store.event_loop.create_task(self._install_extension_async(extension_name))

    async def _install_extension_async(self, extension_name: str) -> None:
        # TODO: async this slow stuff
        # check if the extension is compatible
        logger.info(
            f"Checking compatibility of extension {extension_name} to current Grapycal version..."
        )
        try:
            await self._check_extension_compatible(extension_name)
        except Exception as e:
            logger.error(f"{e}")
            return
        # run pip install
        logger.info(f"Installing extension {extension_name}. This may take a while...")
        pip = await asyncio.create_subprocess_exec("pip", "install", extension_name)
        await pip.wait()

        logger.info(f"Installed extension {extension_name}. Now importing...")
        # import extension
        self.import_extension(extension_name)
        # update available extensions
        await self._update_available_extensions_topic_async()

    def _load_extension(self, name: str) -> Extension:
        extension = self._extensions[name] = get_extension(
            name, set(self._objectsync.get_all_node_types().values())
        )
        self._register_extension(name)
        self._imported_extensions_topic.add(name, extension.get_info())
        for node_type_name, node_type in extension.node_types_d.items():
            main_store.node_types.add(
                node_type_name,
                {
                    "name": node_type_name,
                    "category": node_type.category,
                    "description": node_type.__doc__,
                },
            )
        return extension

    def _register_extension(self, name: str) -> None:
        for node_type_name, node_type in self._extensions[name].node_types_d.items():
            self._objectsync.register(node_type, node_type_name)
            main_store.slash.register(
                node_type_name.split(".")[1][:-4],
                lambda ctx, args, n=node_type_name: self._create_node_slash_listener(
                    ctx, args, n
                ),  # the lambda is necessary to capture the value of n
                source=name,
                prefix="",
            )
        for slash in self._extensions[name].get_slash_commands().values():
            main_store.slash.register(slash["name"], slash["callback"], source=name)

    def _create_node_slash_listener(
        self, ctx: CommandCtx, args: dict, node_type_name: str
    ) -> None:
        translation = args.get("translation", [ctx.mouse_pos[0], ctx.mouse_pos[1]])
        translation = [
            snap_node(translation[0]),
            snap_node(translation[1]),
        ]
        main_store.main_editor.create_node(
            node_type_name,
            sender=ctx.client_id,
            attached_port=args.get("attached_port", None),
            translation=translation,
        )

    def _check_extension_not_used(self, name: str) -> None:
        extension = self._extensions[name]
        node_types = extension.node_types_d
        skip_types = set()  # skip singleton nodes with auto_instantiate=True
        for node_type in extension.singletonNodeTypes.values():
            if node_type._auto_instantiate:
                skip_types.add(
                    extension.add_extension_name_to_node_type(node_type.__name__)
                )

        for obj in main_store.main_editor.top_down_search(type=Node):
            if obj.get_type_name() not in node_types:
                continue
            if obj.is_preview.get():
                continue
            if obj.get_type_name() in skip_types:
                continue
            raise Exception(
                f"Cannot unload extension {name}, there are still {obj.__class__.__name__} in the workspace"
            )

    def _unload_extension(self, name: str) -> None:
        node_types = self._extensions[name].node_types_d
        for node_type in node_types:
            self._objectsync.unregister(node_type)
        self._extensions.pop(name)
        self._imported_extensions_topic.pop(name)
        for node_type_name in node_types:
            main_store.node_types.pop(node_type_name)

    def create_preview_nodes(self, name: str) -> None:
        node_types = self._extensions[name].node_types_d
        for node_type in node_types.values():
            if not node_type.category == "hidden" and not node_type._is_singleton:
                self._objectsync.create_object(
                    node_type,
                    parent_id=main_store.node_library.get_id(),
                    is_preview=True,
                    is_new=True,
                )

    def _destroy_nodes(self, name: str) -> None:
        node_types = self._extensions[name].node_types_d
        for obj in main_store.node_library.get_children_of_type(
            Node
        ) + main_store.main_editor.top_down_search(type=Node):
            if obj.get_type_name() in node_types:
                self._objectsync.destroy_object(obj.get_id())

    def get_extension(self, name: str) -> Extension:
        return self._extensions[name]

    def get_extention_names(self) -> list[str]:
        return list(self._extensions.keys())

    def get_extensions_info(self) -> List[dict]:
        return [extension.get_info() for extension in self._extensions.values()]
