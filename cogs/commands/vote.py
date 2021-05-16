import logging

import discord
from discord.ext import commands

import config
from utils.record import record_usage

log = logging.getLogger(__name__)

class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_role(config.role_staff)
    @commands.before_invoke(record_usage)
    @commands.group()
    async def vote(self, ctx, message: discord.Message = None):
        """ Add vote reactions to a message. """
        async def get_last_message(ctx):
            messages = await ctx.channel.history(limit=2).flatten()
            return messages[1]

        message = message or await get_last_message(ctx)
        try:
            await ctx.message.delete()
            await message.add_reaction(config.emote_yes)
            await message.add_reaction(config.emote_no)
        except Exception as error:
            logging.error(error)
            pass

    @commands.before_invoke(record_usage)
    @vote.command(name="remove")
    async def remove(self, ctx, msgId : int):
        """ Remove reactions from the message ID passed. """
        msg = await ctx.fetch_message(msgId)
        msg.clear_reactions(":yes:778724405333196851")
        msg.clear_reactions(":no:778724416230129705")
            
def setup(bot) -> None:
    """Load the Vote cog."""
    bot.add_cog(VoteCog(bot))
    log.info("Commands loaded: vote")
