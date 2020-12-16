from inspect import trace
import discord
import sys
import utils
from discord.ext import commands
import traceback

import utils  # pylint: disable=import-error

class UtilitiesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.check(utils.is_owner)
    @commands.group()
    async def utilities(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('No utilities subcommand specified.')
    
    @utilities.command(name="ping")
    async def _ping(self ,ctx):
        print("Ping subcommand invoked.")
        await ctx.send(f"Client Latency is:{round(self.bot.latency*1000)}ms.")
    
    @commands.check(utils.is_owner)
    @utilities.command(name="say")
    async def _say(self, ctx, *, args):
        await ctx.send(args)

    @commands.check(utils.is_owner)
    @utilities.command(name="eval")
    async def _eval(self, ctx, *, args):
        embedVar = discord.Embed(title="Evaluating...", color=0xAA45FC).set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        input = f"```py\n{args}\n```"
        embedVar.add_field(name="Input:", value=input, inline=False)
        try:
            input = f"```py\n{args}\n```"
            output = lambda a : args
            embedVar.add_field(name="Output:", value=eval(output(1)), inline=False)
        except:
            e = traceback.format_exc()
            err = "```\n{0}\n```".format(e)
            embedVar.add_field(name="Errors:", value=e, inline=False)
        await ctx.send(embed=embedVar)

def setup(bot):
    bot.add_cog(UtilitiesCog(bot))
