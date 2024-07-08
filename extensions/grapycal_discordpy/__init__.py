from grapycal import Node, FunctionNode
from grapycal.extension_api.trait import InputsTrait, OutputsTrait
from grapycal.sobjects.controls.buttonControl import ButtonControl
from grapycal.sobjects.port import OutputPort
from objectsync.sobject import SObjectSerialized
from grapycal import (
    GenericTopic,
    ListTopic,
    StringTopic,
    func,
    param,
    Edge,
    InputPort,
    task,
)
from topicsync.topic import DictTopic

import discord
from discord import File, app_commands, Interaction, Webhook, Embed, AllowedMentions, ForumTag, Poll
from discord.ext import commands
from discord.utils import MISSING
from discord.ui import View
from discord.abc import Snowflake

from typing import Union, Any, Optional, Sequence, List
import inspect


class BotNode(Node):
    """
    Equivalent to discord.py's `commands.Bot`. It creates a bot instance and sends it out.

    To make it run, send your discord bot token to the `token` input port.

    To make it send out the bot instance, double click on the node.

    :inputs:'
        - token: the discord bot token

    :outputs:
        - bot: the discord bot instance
    """

    category = "discordpy"

    @func()
    def get_bot(self):
        return self.bot

    def build_node(self):
        self.tree_port = self.add_out_port("tree", 64)
        self.token_port = self.add_in_port("token", 1)

    def init_node(self):
        super().init_node()
        self.started = False
        self.bot = commands.Bot(command_prefix="g!", intents=discord.Intents.all())
        self.tree_port.on_edge_connected += self.command_node_conencted
        self.tree_port.on_edge_disconnected += self.command_node_disconnected

        self.token_port.on_activate += self.token_input

    def command_node_conencted(self, edge: Edge, sync=True):
        if not self.started:
            return
        node = edge.get_head().node
        if isinstance(node, CommandNode):
            node.set_bot(self.bot, sync=sync)

    def command_node_disconnected(self, edge: Edge):
        node = edge.get_head().node
        if isinstance(node, CommandNode):
            node.remove_from_bot()

    def token_input(self, port: InputPort):
        self.run(self.start_bot, token=port.get())

    async def start_bot(self, token):
        await self.bot.login(token)
        self.started = True
        for edge in self.tree_port.edges:
            self.command_node_conencted(edge, sync=False)
        await self.bot.connect()

    def destroy(self) -> SObjectSerialized:
        self.run(self.bot.close)
        return super().destroy()


class CommandNode(Node):
    """
    Equivalent to discord.py's `commands.Command`. It adds a command to the bot.

    To make it add a command, send in the bot instance, the command name and the command description to `cmd`.

    To make it sync the commands, double click on the node.

    :inputs:
        - bot: the discord bot instance
        - name: the command name
        - description: the command description

    :outputs:
        - interaction: the interaction
        - *: the parameters
    """

    category = "discordpy"

    @param()
    def param(self, name: str, description: str):
        self.name = name
        self.description = description
        self.set_status("🟠Press to sync")

    def build_node(self):
        self.css_classes.append("fit-content")
        self.output_control = self.add_text_control(
            "", readonly=True, name="output_control"
        )
        self.is_defer = self.add_attribute(
            "is_defer", GenericTopic[bool], False, editor_type="toggle"
        )
        self.interaction_port = self.add_out_port(
            "interaction", 64, display_name="Interaction"
        )
        self.param_ports_topic = self.add_attribute(
            "param_ports_topic",
            ListTopic,
            [],
            editor_type="list",
            display_name="Parameters",
        )
        self.param_type_selector = self.add_attribute(
            "param_type_selector",
            StringTopic,
            "str",
            editor_type="options",
            options=[
                "str",
                "int",
                "bool",
                "User",
                "TextChannel",
                "VoiceChannel",
                "CategoryChannel",
                "Role",
                "Mentionable",
                "float",
                "Attachment",
            ],
            display_name="New Parameter Type",
        )
        self.param_type_dict = self.add_attribute("param_type_dict", DictTopic)
        for param_name, param_type in self.param_type_dict.get().items():
            self.add_out_port(param_name, display_name=f"{param_name}:{param_type}")
        self.sync_button = self.add_button_control("Sync Commands")
        self.tree_port = self.add_in_port("tree", 1)

    def init_node(self):
        self.bot = None
        self.param_ports_topic.on_insert.add_auto(self.on_param_insert)
        self.param_ports_topic.on_pop.add_auto(self.on_param_pop)
        self.sync_button.on_click += lambda: self.run(self.add_and_sync)
        self.set_status("")

    def on_param_insert(self, param_name, _):
        self.add_out_port(
            param_name, display_name=f"{param_name}:{self.param_type_selector.get()}"
        )
        self.param_type_dict[param_name] = self.param_type_selector.get()
        self.set_status("🟠Press to sync")

    def on_param_pop(self, param_name, _):
        self.remove_out_port(param_name)
        self.param_type_dict.pop(param_name)
        self.set_status("🟠Press to sync")

    @task
    def set_bot(self, bot: commands.Bot, sync: bool):
        self.bot = bot
        if sync:
            self.add_and_sync()
        else:
            self.add_command(bot, self.name, self.description)
            self.set_status("🟢Command synced")

    @task
    def remove_from_bot(self):
        self.bot.tree.remove_command(self.name)
        self.bot = None
        self.set_status("")

    def add_and_sync(self):
        if self.bot is None:
            self.print_exception(
                "Not connected to a bot. Please connect 'tree' port to a DiscordBotNode"
            )
        self.run(
            self.async_add_and_sync,
            bot=self.bot,
            name=self.name,
            description=self.description,
        )

    async def callback(self, interaction: Interaction, params):
        if self.is_defer.get():
            await interaction.response.defer()

        self.get_out_port("interaction").push(interaction)
        for name in params:
            self.get_out_port(name).push(params[name])

    def set_status(self, status: str):
        self.sync_button.label.set(status)

    """
    Utility function to sync the commands
    """

    async def async_add_and_sync(self, bot: commands.Bot, name, description):
        self.add_command(bot, name, description)
        await self.sync(bot)

    async def sync(self, bot: commands.Bot):
        await bot.tree.sync()
        self.set_status("🟢Command synced")

    def add_command(self, bot: commands.Bot, name, description):
        params = self.param_type_dict.get()

        async def callback(interaction: Interaction, **params):
            await self.callback(interaction, params)

        parameters = [
            # Required parameter
            inspect.Parameter(
                name="interaction",  # Parameter name
                annotation=discord.Interaction,  # Parameter type
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ),
        ]
        types = {
            "str": str,
            "int": int,
            "bool": bool,
            "User": discord.User,
            "TextChannel": discord.TextChannel,
            "VoiceChannel": discord.VoiceChannel,
            "CategoryChannel": discord.CategoryChannel,
            "Role": discord.Role,
            "Mentionable": Union[discord.User, discord.Role],
            "float": float,
            "Attachment": discord.Attachment,
        }
        for n, t in params.items():
            parameters.append(
                inspect.Parameter(
                    name=n,
                    annotation=types[t],
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
            )

        callback.__signature__ = inspect.Signature(parameters)  # type: ignore
        command = app_commands.Command(
            name=name,
            description=description,
            callback=callback,
        )

        bot.tree.remove_command(name)
        bot.tree.add_command(command)


class SendMessageNode(Node):
    """
    Equivalent to discord.py's `Interaction.send_message if command hasn't deferred, else Interaction.followup.send`. It sends a message to the interaction.

    To make it send the message, send in the interaction and content to `content`.

    
    :inputs:
        - interaction: the interaction
        - content: the message content
        - embed: the embed
        - embeds: the list of embeds
        - file: the file
        - files: the list of files
        - tts: whether the message should be tts
        - view: the view
        - ephemeral: whether the message should be ephemeral
        - allowed_mentions: the allowed mentions
        - suppress_embeds: whether to suppress embeds
        - silent: whether to suppress errors
        - delete_after: the time after which the message should be deleted
        - poll: the poll

    :outputs:
        - None
    """

    category = "discordpy/interaction/response"

    @func(shown_ports=["interaction", "content"])
    def send_message(
        self, 
        interaction: Interaction, 
        content: str, 
        embed: discord.Embed = MISSING, embeds: Sequence[discord.Embed] = MISSING, 
        file: discord.File = MISSING, files: Sequence[discord.File] = MISSING, 
        tts: bool = False,
        view: discord.ui.View = MISSING,
        ephemeral: bool = False,
        allowed_mentions: discord.AllowedMentions = MISSING,
        suppress_embeds: bool = False,
        silent: bool = False,
        delete_after: Optional[float] = None,
        poll: discord.Poll = MISSING,
        ):
        print("Sending message")
        if interaction.response.is_done():
            self.print_exception("Interaction already responded, If message is deferred, use WebhookSend")
        self.run(self.async_send_message, interaction=interaction, content=content, embed=embed, embeds=embeds, file=file, files=files, tts=tts, view=view, ephemeral=ephemeral, allowed_mentions=allowed_mentions, suppress_embeds=suppress_embeds, silent=silent, delete_after=delete_after, poll=poll)

    async def async_send_message(self, interaction:Interaction, content, embed, embeds, file, files, tts, view, ephemeral, allowed_mentions, suppress_embeds, silent, delete_after, poll):
        await interaction.response.send_message(content=content, embed=embed, embeds=embeds, file=file, files=files, tts=tts, view=view, ephemeral=ephemeral, allowed_mentions=allowed_mentions, suppress_embeds=suppress_embeds, silent=silent, delete_after=delete_after, poll=poll)


class WebhookSendNode(Node):
    """
    Equivalent to discord.py's `Webhook.send`. It sends a message to the webhook.

    To make it send the message, send in the webhook and content to `content`.


    :inputs:
        - webhook: the webhook
        - content: the message content
        - username: the username
        - avatar_url: the avatar url
        - tts: whether the message should be tts
        - ephemeral: whether the message should be ephemeral
        - file: the file
        - files: the list of files
        - embed: the embed
        - embeds: the list of embeds
        - allowed_mentions: the allowed mentions
        - view: the view
        - thread: the thread
        - thread_name: the thread name
        - wait: whether to wait
        - suppress_embeds: whether to suppress embeds
        - silent: whether to suppress errors
        - applied_tags: the applied tags
        - poll: the poll
    
    :outputs:
        - None
    """
    category = "discordpy/webhook"

    @func(shown_ports=["webhook", "content"])
    def send(
        self,
        webhook: Webhook,
        content: str,
        username: Optional[str] = MISSING,
        avatar_url: Any = MISSING,
        tts: bool = False,
        ephemeral: bool = False,
        file: File = MISSING,
        files: Sequence[File] = MISSING,
        embed: Embed = MISSING,
        embeds: Sequence[Embed] = MISSING,
        allowed_mentions: AllowedMentions = MISSING,
        view: View = MISSING,
        thread: Snowflake = MISSING,
        thread_name: Optional[str] = MISSING,
        wait: bool = False,
        suppress_embeds: bool = False,
        silent: bool = False,
        applied_tags: List[ForumTag] = MISSING,
        poll: Poll = MISSING,
    ):
        self.run(self.async_send, webhook=webhook, content=content, username=username, avatar_url=avatar_url, tts=tts, ephemeral=ephemeral, file=file, files=files, embed=embed, embeds=embeds, allowed_mentions=allowed_mentions, view=view, thread=thread, thread_name=thread_name, wait=wait, suppress_embeds=suppress_embeds, silent=silent, applied_tags=applied_tags, poll=poll)
    
    async def async_send(self, webhook: Webhook, content: str, username, avatar_url, tts, ephemeral, file, files, embed, embeds, allowed_mentions, view, thread, thread_name, wait, suppress_embeds, silent, applied_tags, poll):
        await webhook.send(content=content, username=username, avatar_url=avatar_url, tts=tts, ephemeral=ephemeral, file=file, files=files, embed=embed, embeds=embeds, allowed_mentions=allowed_mentions, view=view, thread=thread, thread_name=thread_name, wait=wait, suppress_embeds=suppress_embeds, silent=silent, applied_tags=applied_tags, poll=poll)
             


class FileNode(Node):
    @func(
        sign_source=[discord.File.__init__],
        annotation_override={"spoiler": bool, "description": str},
        default_override={"spoiler": False, "description": ""},
    )
    def file(self, **kwargs):
        return File(**kwargs)

del FunctionNode, Node
