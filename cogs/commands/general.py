import logging

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Cog, Context

from utils import embeds
from utils.record import record_usage

log = logging.getLogger(__name__)


class General(Cog):
    """ General Commands Cog """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name='profile_picture', aliases=['pfp'])
    async def pfp(self, ctx: Context, user: discord.User = None):
        """ Returns the profile picture of the invoker or the mentioned user. """

        user = user or ctx.author
        embed = embeds.make_embed(context=ctx)
        embed.set_image(url=user.avatar_url)
        await ctx.send(embed=embed)
            

    @commands.has_role("Staff")
    @commands.before_invoke(record_usage)
    @commands.command(name="boosttest")
    async def boosttest(self, ctx: Context):
        embed = embeds.make_embed(context=ctx, author=False)
        embed.title = "THANK YOU FOR THE BOOST!"
        embed.description = "In ornare est augue, at malesuada quam gravida id. Sed hendrerit ipsum congue, tristique nibh non, faucibus lorem. Fusce maximus risus nec rhoncus posuere. Vestibulum sapien erat, vehicula eget lorem ac, semper egestas mi. Maecenas sit amet cursus quam. Morbi non tincidunt ex. Curabitur vel pellentesque metus, vitae semper odio. Aliquam nec lectus convallis, placerat sapien ut, aliquet neque. Mauris feugiat ac arcu vel sollicitudin. Nam aliquet a sapien in auctor. Vestibulum consectetur molestie finibus."
        embed.set_image(url="https://i.imgur.com/O8R98p9.gif")
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    """ Load the General cog. """
    bot.add_cog(General(bot))
    log.info("Cog loaded: General")
