import logging

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
    async def vote(self, ctx, msg_id: int = None):
        """ Add vote reactions to a message. """
        await ctx.message.delete()
        
        # add to previous message
        if not msg_id:
            last_msg = self.bot.cached_messages[-2]
            await last_msg.add_reaction(config.emote_yes)
            await last_msg.add_reaction(config.emote_no)
            return
        
        # add the check and cross to the previous message.
        msg = await ctx.fetch_message(msg_id)
        await msg.add_reaction(config.emote_yes)
        await msg.add_reaction(config.emote_no)
        return

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
