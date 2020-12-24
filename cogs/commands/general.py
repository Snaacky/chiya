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

    
    # This is an example of a embed command
    @commands.before_invoke(record_usage)
    @commands.command(name='pfp')
    async def _pfp(self, ctx):
        
        embed = discord.Embed(name="Profile Picture", description=f"[Link]({ctx.author.avatar_url})")
        embed.set_author(name=ctx.author,
                         icon_url=ctx.author.avatar_url)
        embed.set_image(url=ctx.author.avatar_url)

        await ctx.send(embed=embed)

# The setup function below is necessary. Remember we give bot.add_cog() the name of the class in this case SimpleCog.
# When we load the cog, we use the name of the file.
def setup(bot) -> None:
    """Load the SimpleCog cog."""
    bot.add_cog(GeneralCommandsCog(bot))
    log.info("Cog loaded: GeneralCommandsCog")