import logging

from discord.ext import commands
from utils import embeds
from utils.record import record_usage

log = logging.getLogger(__name__)


class GeneralCommandsCog(commands.Cog):
    """GeneralCommandsCog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.command(name="pfp", aliases=["avi", "pp", "avatar", "profilepic"])
    async def pfp(self, ctx, user=None):
        """ Returns the profile picture of the invoker or the mentioned user. """

        embed = embeds.make_embed(context=ctx)

        # Attempt to return the avatar of a mentioned user if the parameter was not none.
        if user is not None:
            member = await commands.MemberConverter().convert(ctx, user)
            if member:
                embed.set_image(url=member.avatar_url)
            else:
                raise commands.UserNotFound(user)
        # Otherwise, assume the invoker just wanted their only avatar and return that.
        else:
            embed.set_image(url=ctx.message.author.avatar_url)
        await ctx.send(embed=embed)
    

    @commands.before_invoke(record_usage)
    @commands.command(name="boosttest")
    async def boosttest(self, ctx):
        embed = embeds.make_embed(context=ctx, author=False)
        embed.title = "THANK YOU FOR THE BOOST!"
        embed.description = "In ornare est augue, at malesuada quam gravida id. Sed hendrerit ipsum congue, tristique nibh non, faucibus lorem. Fusce maximus risus nec rhoncus posuere. Vestibulum sapien erat, vehicula eget lorem ac, semper egestas mi. Maecenas sit amet cursus quam. Morbi non tincidunt ex. Curabitur vel pellentesque metus, vitae semper odio. Aliquam nec lectus convallis, placerat sapien ut, aliquet neque. Mauris feugiat ac arcu vel sollicitudin. Nam aliquet a sapien in auctor. Vestibulum consectetur molestie finibus."
        embed.set_image(url="https://i.imgur.com/O8R98p9.gif")
        await ctx.send(embed=embed)


def setup(bot) -> None:
    """ Load the GeneralCog cog. """
    bot.add_cog(GeneralCommandsCog(bot))
    log.info("Cog loaded: GeneralCommandsCog")
