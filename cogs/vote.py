import discord
import sys
from discord.ext import commands

import utils  # pylint: disable=import-error

class Vote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @vote.command(name="remove")
    async def remove(ctx, msgId : int):
        msg = await ctx.fetch_message(msgId)
        msgId.clear_reactions(":yes:778724405333196851")
        msgId.clear_reactions(":no:778724416230129705")
        #remove reactions from the message ID passed.
            

    

def setup(bot):
    bot.add_cog(Vote(bot))
