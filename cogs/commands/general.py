import logging
import discord

from discord.ext import commands
from utils import embeds
from utils.record import record_usage


# Enabling logs
log = logging.getLogger(__name__)


class GeneralCommandsCog(commands.Cog):
    """GeneralCommandsCog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.command(name='pfp')
    async def pfp(self, ctx, user=None):
        # Return the mentioned user or the ID of the user specified
        if user is not None:
            user = int(user.strip("<@!>"))
            user = ctx.message.guild.get_member(user)
            if user:
                embed = discord.Embed()
                embed.set_author(name=user, icon_url=user.avatar_url)
                embed.set_image(url=user.avatar_url)
                await ctx.send(embed=embed)
        # Return the command invokers pfp if no params passed 
        else:
            embed = discord.Embed()
            embed.set_author(name=ctx.message.author, icon_url=ctx.message.author.avatar_url)
            embed.set_image(url=ctx.message.author.avatar_url)
            await ctx.send(embed=embed)

        

# The setup function below is necessary. Remember we give bot.add_cog() the name of the class in this case SimpleCog.
# When we load the cog, we use the name of the file.
def setup(bot) -> None:
    """Load the SimpleCog cog."""
    bot.add_cog(GeneralCommandsCog(bot))
    log.info("Cog loaded: GeneralCommandsCog")
