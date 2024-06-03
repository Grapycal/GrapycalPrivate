from grapycal import Node, FunctionNode
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from grapycal.extension_api.trait import InputsTrait, OutputsTrait
from grapycal.sobjects.port import InputPort

class DiscordBotNode(Node):
    category = 'discordpy'

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
        self.bot = commands.Bot(command_prefix='g!', intents=discord.Intents.all())
        self.bot.tree.add_command

    def double_click(self):
        self.outs.push('bot', self.bot)
    
    def task(self, token):
        self.run(self.start_bot, token=token)
        self.outs.push('bot', self.bot)
           
    async def start_bot(self, token):
        await self.bot.login(token)
        await self.bot.connect()

class DiscordCommandNode(Node):
    category = 'discordpy'

    def define_traits(self):
        self.cmd = InputsTrait(
            name="cmd",
            attr_name="cmd",
            ins=["bot", "cmd_name", "cmd_description"],
        )

        self.cmd_param = InputsTrait(
            name="cmd_param",
            attr_name="cmd_param",
            ins=[],
            expose_attr = True,
        )
        return [self.cmd, self.cmd_param]
    