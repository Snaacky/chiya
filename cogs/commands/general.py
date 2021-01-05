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
    async def pfp(self, ctx, mention=None):
        # Return the mentioned users profile picture
        if mention:
            user = ctx.message.guild.get_member(ctx.message.mentions[0].id)
            embed = discord.Embed(name="Profile Picture", description=f"[Link]({user.avatar_url})")
            embed.set_author(name=user, icon_url=user.avatar_url)
            embed.set_image(url=user.avatar_url)
            await ctx.send(embed=embed)
        else:
            # Returns the user who invoked the commands profile picture
            embed = discord.Embed(name="Profile Picture", description=f"[Link]({ctx.author.avatar_url})")
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            embed.set_image(url=ctx.author.avatar_url)
            await ctx.send(embed=embed)


# The setup function below is necessary. Remember we give bot.add_cog() the name of the class in this case SimpleCog.
# When we load the cog, we use the name of the file.
def setup(bot) -> None:
    """Load the SimpleCog cog."""
    bot.add_cog(GeneralCommandsCog(bot))
    log.info("Cog loaded: GeneralCommandsCog")
