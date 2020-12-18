from discord.ext import commands
# from utils import utils
# import logging
import discord

# log = logging.getLogger(__name__)


class error_handle(commands.Cog):
    """error_handle"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, exception):
        # log.error(f"on_command_error: {ctx.author} | {exception}")

        try:
            
            await ctx.send(exception)
        except discord.errors.Forbidden:
            await ctx.send(exception)


def setup(bot):
    bot.add_cog(error_handle(bot))
