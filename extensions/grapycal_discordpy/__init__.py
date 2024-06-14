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
            expose_attr = True,
        )
        
        self.cb = OutputsTrait(
            outs=["callback"],
        )
        return [self.cmd, self.cmd_params, self.cb]
    
    def double_click(self):
        if self.bot:
            self.run(self.sync)

    async def sync(self):
        await self.bot.tree.sync()
    
    def task(self, **kwargs):
        bot:commands.Bot = kwargs['bot']
        self.bot = bot
        cmd_name = kwargs['cmd_name']
        cmd_description = kwargs['cmd_description']
        global cb
        cb = self.cb
        

        params = kwargs.copy()
        for key in ['bot', 'cmd_name', 'cmd_description']:
            params.pop(key)
        params_str = ', '.join([f'{key}:{value}' for key, value in params.items()])
        params_str_without_type = ', '.join(params.keys())
        
        try:
            bot.tree.remove_command(cmd_name)
        except:
            pass

        exec(f'@bot.tree.command(name="{cmd_name}", description="{cmd_description}")\n'
             f'async def {cmd_name}(interaction:Interaction, {params_str}):\n'
             f'    cb.push("callback", (interaction, {params_str_without_type}))\n'
             f'bot.tree.add_command({cmd_name}, override=True)')
        
class DiscordInterRespSendMsgNode(Node):
    category = 'discordpy'

    def define_traits(self):
        self.ins = InputsTrait(
            ins=["interaction", "content"],
            on_all_ready=self.task,
        )
        return [self.ins]
    
    def task(self, interaction:Interaction, content):
        self.run(self.send, interaction=interaction, content=content)

    async def send(self, interaction:Interaction, content):
        await interaction.response.send_message(content=content)
