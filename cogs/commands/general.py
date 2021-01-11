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
            user_strip = int(user.strip("<@!>"))
            member = ctx.message.guild.get_member(user_strip)
            if member:
                embed.set_image(url=member.avatar_url)
            else:
                raise commands.UserNotFound(user)
        # Otherwise, assume the invoker just wanted their only avatar and return that.
        else:
            embed.set_image(url=ctx.message.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.before_invoke(record_usage)
    @commands.command(name='addemoji', aliases=['ae', 'adde'    ])
    async def addemoji(self, ctx, emoji=None, msg_id=None):
        """ Add the given emoji as a reaction to the specified message, or the previous message. """
        if emoji:
            if msg_id:
                msg = await ctx.fetch_message(msg_id)
                await msg.add_reaction(emoji)
                return

            msg = (await ctx.channel.history(limit=3).flatten())[2]
            await msg.add_reaction(emoji)

        



def setup(bot) -> None:
    """ Load the GeneralCog cog. """
    bot.add_cog(GeneralCommandsCog(bot))
    log.info("Cog loaded: GeneralCommandsCog")
