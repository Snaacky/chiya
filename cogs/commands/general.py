import logging
from typing import Union

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Cog, Context

import config
from utils import embeds
from utils.record import record_usage

log = logging.getLogger(__name__)


class General(Cog):
    """ General Commands Cog """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name='profile_picture', aliases=["pfp", "avi", "pp", "avatar", "profilepic", "av"])
    async def pfp(self, ctx: Context, user: discord.User = None):
        """ Returns the profile picture of the invoker or the mentioned user. """

        user = user or ctx.author
        embed = embeds.make_embed(context=ctx)
        embed.set_image(url=user.avatar_url)
        await ctx.send(embed=embed)


    @commands.bot_has_permissions(read_message_history=True, add_reactions=True)
    @commands.before_invoke(record_usage)
    @commands.command(name='addemoji', aliases=['ae', 'adde'])
    async def addemoji(self, ctx, message: discord.Message, *emojis: Union[discord.Emoji, discord.PartialEmoji, discord.Reaction, str]):
        """ Add the given emojis as a reaction to the specified message. """

        for emoji in emojis:
            try:
                await message.add_reaction(emoji)
                await ctx.message.delete()
            except discord.errors.HTTPException:
                pass



def setup(bot: Bot) -> None:
    """ Load the General cog. """
    bot.add_cog(General(bot))
    log.info("Cog loaded: General")
