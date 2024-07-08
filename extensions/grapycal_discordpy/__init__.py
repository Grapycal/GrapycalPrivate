from grapycal import Node, FunctionNode
import discord
from discord import File, app_commands, Interaction
from discord.ext import commands
from grapycal.extension_api.trait import InputsTrait, OutputsTrait
from grapycal.sobjects.controls.buttonControl import ButtonControl
from grapycal.sobjects.port import OutputPort
from objectsync.sobject import SObjectSerialized
import inspect
from typing import Union
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


class DiscordBotNode(Node):
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
        if isinstance(node, DiscordCommandNode):
            node.set_bot(self.bot, sync=sync)

    def command_node_disconnected(self, edge: Edge):
        node = edge.get_head().node
        if isinstance(node, DiscordCommandNode):
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


class DiscordCommandNode(Node):
    """
    Equivalent to discord.py's `commands.Command`. It adds a command to the bot.

    To make it add a command, send in the bot instance, the command name and the command description to `cmd`.

    To make it sync the commands, double click on the node.

    :inputs:
        - bot: the discord bot instance
        - cmd_name: the command name
        - cmd_description: the command description

    :outputs:
        - interaction: the interaction
        - *: the parameters
    """

    category = "discordpy"

    @param()
    def param(self, cmd_name: str, cmd_description: str):
        self.cmd_name = cmd_name
        self.cmd_description = cmd_description
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
            self.add_command(bot, self.cmd_name, self.cmd_description)
            self.set_status("🟢Command synced")

    @task
    def remove_from_bot(self):
        self.bot.tree.remove_command(self.cmd_name)
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
            cmd_name=self.cmd_name,
            cmd_description=self.cmd_description,
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

    async def async_add_and_sync(self, bot: commands.Bot, cmd_name, cmd_description):
        self.add_command(bot, cmd_name, cmd_description)
        await self.sync(bot)

    async def sync(self, bot: commands.Bot):
        await bot.tree.sync()
        self.set_status("🟢Command synced")

    def add_command(self, bot: commands.Bot, cmd_name, cmd_description):
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
            name=cmd_name,
            description=cmd_description,
            callback=callback,
        )

        bot.tree.remove_command(cmd_name)
        bot.tree.add_command(command)


class DiscordSendMessageNode(Node):
    """
    Equivalent to discord.py's `Interaction.send_message if command hasn't deferred, else Interaction.followup.send`. It sends a message to the interaction.

    To make it send the message, send in the interaction and content to `content`.

    :inputs:
        - interaction: discord.Interaction
        - content: the message content

    :outputs:
        - None
    """

    category = "discordpy"

    @func(
        sign_source=[
            inspect.Parameter(
                name="interaction",
                annotation=discord.Interaction,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ),
            discord.Webhook.send,
        ],
        shown_ports=["interaction", "content"],
    )
    def task(self, interaction: Interaction, **kwargs):
        self.run(self.send, interaction=interaction, kwargs=kwargs)

    async def send(self, interaction: Interaction, kwargs):
        if interaction.response.is_done():
            await interaction.followup.send(**kwargs)
        else:
            await interaction.response.send_message(**kwargs)


class DiscordFileNode(Node):
    @func(
        sign_source=[discord.File.__init__],
        annotation_override={"spoiler": bool, "description": str},
        default_override={"spoiler": False, "description": ""},
    )
    def file(self, **kwargs):
        return File(**kwargs)


del FunctionNode, Node
