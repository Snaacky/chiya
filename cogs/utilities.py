from inspect import trace
import sys
import traceback
import logging

import discord
from discord.ext import commands

import utils  # pylint: disable=import-error
from record import record_usage # pylint: disable=import-error


# Enabling logs
log = logging.getLogger(__name__)


class UtilitiesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.is_owner()
    @commands.group()
    async def utilities(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('No utilities subcommand specified.')

    @utilities.command(name="ping")
    async def _ping(self ,ctx):
        print("Ping subcommand invoked.")
        await ctx.send(f"Client Latency is:{round(self.bot.latency*1000)}ms.")


    @utilities.command(name="say")
    async def _say(self, ctx, *, args):
        await ctx.send(args)


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


def setup(bot) -> None:
    """Load the UtilitiesCog cog."""
    bot.add_cog(UtilitiesCog(bot))
    log.info("Cog loaded: UtilitiesCog")
