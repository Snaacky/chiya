from discord.ext import commands

import embeds
import discord


class error_handle(commands.Cog):
    """error_handle"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, exception):

        try:
            
            await ctx.send(exception)
        except discord.errors.Forbidden:
            await ctx.send(exception)


def setup(bot):
    bot.add_cog(error_handle(bot))
