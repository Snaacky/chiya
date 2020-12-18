import logging

from discord.ext import commands
import discord

import embeds


# Enabling logs
log = logging.getLogger(__name__)


class error_handle(commands.Cog):
    """error_handle"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, exception):

        try:
            await embeds.error_message(ctx, description=exception)
        except discord.errors.Forbidden: # This would happend if bot does not have the perms to post embeds.
            await ctx.send(exception)


def setup(bot) -> None:
    """Load the error_handle cog."""
    bot.add_cog(error_handle(bot))
    log.info("Cog loaded: error_handle")
