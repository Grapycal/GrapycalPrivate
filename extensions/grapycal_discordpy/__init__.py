from grapycal import Node, FunctionNode
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from grapycal.extension_api.trait import InputsTrait, OutputsTrait
from grapycal.sobjects.port import OutputPort
from objectsync.sobject import SObjectSerialized
import inspect
from typing import Union
from grapycal import GenericTopic, ListTopic, StringTopic
from topicsync.topic import DictTopic

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
    '''
    category = "discordpy"

    def define_traits(self): # type: ignore
        self.cmd = InputsTrait(
            name="cmd",
            attr_name="cmd",
            ins=["bot", "cmd_name", "cmd_description"],
            on_all_ready=self.task,
        )
        return [self.cmd]
    
    def build_node(self):
        self.css_classes.append("fit-content")
        self.output_control = self.add_text_control("", readonly=True, name="output_control")
        self.is_defer = self.add_attribute("is_defer", GenericTopic[bool], False, editor_type="toggle")
        self.interaction_port = self.add_out_port("interaction", 1, display_name="Interaction")
        self.param_ports_topic = self.add_attribute("param_ports_topic", ListTopic, [], editor_type="list", display_name="Parameters")
        self.param_type_selector = self.add_attribute("param_type_selector", StringTopic, "str", editor_type="options", options=["str", "int", "bool", "User", "TextChannel", "VoiceChannel", "CategoryChannel", "Role", "Mentionable", "float", "Attachment"], display_name="New Parameter Type")
        self.param_type_dict = self.add_attribute("param_type_dict", DictTopic)
        for param_name, param_type in self.param_type_dict.get().items():
            self.add_out_port(param_name, display_name=f'{param_name}:{param_type}')

    def init_node(self):
        self.param_ports_topic.on_insert.add_auto(self.on_param_insert)
        self.param_ports_topic.on_pop.add_auto(self.on_param_pop)

    def on_param_insert(self, param_name, _):
        self.add_out_port(param_name,display_name=f'{param_name}:{self.param_type_selector.get()}')
        self.param_type_dict[param_name] = self.param_type_selector.get()
    
    def on_param_pop(self, param_name, _):
        self.remove_out_port(param_name)
        self.param_type_dict.pop(param_name)
        
    def double_click(self):
        if self.bot:
            self.run(self.sync)

    async def sync(self):
        await self.bot.tree.sync()
        self.output_control.set("Commands synced")

    def task(self, **kwargs):
        self.bot:commands.Bot = kwargs["bot"]
        self.run(self.add_command, **kwargs)

    def callback(self, interaction: Interaction, params):
        self.get_out_port("interaction").push(interaction)
        for name in params:
            self.get_out_port(name).push(params[name])
    
    def add_command(self, bot: commands.Bot, cmd_name, cmd_description):
        params = self.param_type_dict.get()

        if self.is_defer.get():
            async def callback(interaction:Interaction, **params):
                await interaction.response.defer()
                self.callback(interaction, params)
        else:
            async def callback(interaction:Interaction, **params):
                self.callback(interaction, params)

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

        callback.__signature__ = inspect.Signature(parameters) # type: ignore
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

    def define_traits(self): # type: ignore
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
