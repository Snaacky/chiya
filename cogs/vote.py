import sys
import logging

import discord
from discord.ext import commands

import utils  # pylint: disable=import-error
from record import record_usage # pylint: disable=import-error


# Enabling logs
log = logging.getLogger(__name__)


class Vote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.group()
    async def vote(self, ctx, msgId : int):
        if (msgId is None):
            last_message_ID = self.bot.cached_messages[len(self.bot.cached_messages)-1]
            await last_message_ID.add_reaction(":yes:778724405333196851")
            await last_message_ID.add_reaction(":no:778724416230129705")
            # add to previous message
            return
        
        msg = await ctx.fetch_message(msgId)
        await msg.add_reaction(":yes:778724405333196851")
        await msg.add_reaction(":no:778724416230129705")
        return
        # add the check and cross to the previous message.

    @commands.before_invoke(record_usage)
    @vote.command(name="remove")
    async def remove(self, ctx, msgId : int):
        msg = await ctx.fetch_message(msgId)
        msg.clear_reactions(":yes:778724405333196851")
        msg.clear_reactions(":no:778724416230129705")
        #remove reactions from the message ID passed.
            

def setup(bot) -> None:
    """Load the Vote cog."""
    bot.add_cog(Vote(bot))
    log.info("Cog loaded: Vote")