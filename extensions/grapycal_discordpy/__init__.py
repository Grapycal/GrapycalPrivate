from grapycal import Node, FunctionNode
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from grapycal.extension_api.trait import InputsTrait, OutputsTrait
from grapycal.sobjects.port import InputPort
from objectsync.sobject import SObjectSerialized
import inspect
from typing import Union
from topicsync.topic import GenericTopic

class DiscordBotNode(Node):
    '''
    Equivalent to discord.py's `commands.Bot`. It creates a bot instance and sends it out.

    To make it run, send your discord bot token to the `token` input port.

    To make it send out the bot instance, double click on the node.

    :inputs:'
        - token: the discord bot token
    
    :outputs:
        - bot: the discord bot instance
    '''
    category = "discordpy"

    def define_traits(self):
        self.ins = InputsTrait(
            ins=["token"],
            on_all_ready=self.task,
        )
        self.outs = OutputsTrait(
            outs=["bot"],
        )
        return [self.ins, self.outs]

    def init_node(self):
        super().init_node()
        self.bot = commands.Bot(command_prefix="g!", intents=discord.Intents.all())

    def double_click(self):
        self.outs.push("bot", self.bot)

    def task(self, token):
        self.run(self.start_bot, token=token)
        self.outs.push("bot", self.bot)

    async def start_bot(self, token):
        await self.bot.login(token)
        await self.bot.connect()

    def destroy(self) -> SObjectSerialized:
        self.run(self.bot.close)
        return super().destroy()


class DiscordCommandNode(Node):
    '''
    Equivalent to discord.py's `commands.Command`. It creates a command and sends out the interaction and parameters.

    To make it add the command to bot.tree (local command tree), send in the bot instance, command name to `cmd_name` and command description to `cmd_description`.

    To make it sync to discord, double click on the node.

    It runs when the command is invoked by the user in discord.

    :inputs:
        - bot: the discord bot instance
        - cmd_name: the command name
        - cmd_description: the command description
        - cmd_params: the parameters of the command (optional)
    :outputs:
        - interaction: discord.Interaction
        - params: the parameters passed to the command, data looks like {param1: value1, param2: value2, ...}
    '''
    category = "discordpy"

    def init_node(self):
        self.bot = None

    def define_traits(self):
        self.cmd = InputsTrait(
            name="cmd",
            attr_name="cmd",
            ins=["bot", "cmd_name", "cmd_description"],
            on_all_ready=self.task,
        )

        self.cmd_params = InputsTrait(
            name="cmd_params",
            attr_name="cmd_params",
            ins=[],
            expose_attr=True,
        )

        self.cb = OutputsTrait(
            outs=["interaction", "params"],
        )
        return [self.cmd, self.cmd_params, self.cb]
    
    def build_node(self):
        self.output_control = self.add_text_control(
            "", readonly=True, name="output_control"
        )
        self.is_defer = self.add_attribute(
            "is_defer", GenericTopic[bool], False, editor_type="toggle"
        )
        self.css_classes.append("fit-content")

    def double_click(self):
        if self.bot:
            self.run(self.sync)

    async def sync(self):
        await self.bot.tree.sync()
        self.output_control.set("Commands synced")

    def task(self, **kwargs):
        bot: commands.Bot = kwargs["bot"]
        self.bot = bot
        cmd_name = kwargs['cmd_name']
        cmd_description = kwargs['cmd_description']

        params = kwargs.copy()
        for key in ["bot", "cmd_name", "cmd_description"]:
            params.pop(key)
        
        if self.is_defer.get():
            async def callback(interaction:Interaction, **params):
                await interaction.response.defer()
                self.cb.push('interaction', interaction)
                self.cb.push('params', params)
        else:
            async def callback(interaction:Interaction, **params):
                self.cb.push('interaction', interaction)
                self.cb.push('params', params)

        parameters = [
            # Required parameter
            inspect.Parameter(
                name='interaction', # Parameter name
                annotation=discord.Interaction, # Parameter type
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

        callback.__signature__ = inspect.Signature(parameters)
        command = app_commands.Command(
            name=cmd_name,
            description=cmd_description,
            callback=callback,
        )
        
        bot.tree.remove_command(cmd_name)
        bot.tree.add_command(command)
        self.output_control.set(f"Command {cmd_name} added")

class DiscordSendMessageNode(Node):
    '''
    Equivalent to discord.py's `Interaction.send_message if command hasn't deferred, else Interaction.followup.send`. It sends a message to the interaction.

    To make it send the message, send in the interaction and content to `content`.

    :inputs:
        - interaction: discord.Interaction
        - content: the message content
    
    :outputs:
        - None
    '''
    category = "discordpy"

    def define_traits(self):
        self.ins = InputsTrait(
            ins=["interaction", "content"],
            on_all_ready=self.task,
        )
        return [self.ins]

    def task(self, interaction: Interaction, content):
        self.run(self.send, interaction=interaction, content=content)

    async def send(self, interaction: Interaction, content):
        if interaction.response.is_done():
            await interaction.followup.send(content=content)
        else:
            await interaction.response.send_message(content=content)
