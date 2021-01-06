import logging
import discord

from discord.ext import commands
from utils import embeds
from utils.record import record_usage

log = logging.getLogger(__name__)


class GeneralCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.command(name="pfp", aliases=["avi", "pp", "avatar", "profilepic"])
    async def pfp(self, ctx, user=None):
        """ Returns the profile picture of the invoker or the mentioned user. """
        # Attempt to return the avatar of a mentioned user if the parameter was not none.
        if user is not None:
            user = int(user.strip("<@!>"))  
            user = ctx.message.guild.get_member(user)
            # TODO: Implement an error embed here if the user ID is invalid.
            if user:
                embed = discord.Embed()
                embed.set_author(name=user, icon_url=user.avatar_url)
                embed.set_image(url=user.avatar_url)
                await ctx.send(embed=embed)
        # Otherwise, assume the invoker just wanted their only avatar and return that.
        else:
            embed = discord.Embed()
            embed.set_author(name=ctx.message.author, icon_url=ctx.message.author.avatar_url)
            embed.set_image(url=ctx.message.author.avatar_url)
            await ctx.send(embed=embed)


# The setup function below is necessary. Remember we give bot.add_cog() the name of the class in this case SimpleCog.
# When we load the cog, we use the name of the file.
def setup(bot) -> None:
    """ Load the GeneralCog cog. """
    bot.add_cog(GeneralCommandsCog(bot))
    log.info("Cog loaded: GeneralCommandsCog")
