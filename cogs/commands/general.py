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
        embed = embeds.make_embed(ctx=ctx)
        embed.set_image(url=user.avatar_url)
        await ctx.send(embed=embed)

    @commands.has_role(config.role_staff)
    @commands.command(aliases=["population", "pop"])
    async def count(self, ctx):
        """Returns the current guild member count."""
        await ctx.send(ctx.guild.member_count)

    @commands.bot_has_permissions(read_message_history=True, add_reactions=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="addemoji", aliases=["ae", "adde"])
    async def addemoji(self, ctx, message: discord.Message, *emojis: Union[discord.Emoji, discord.PartialEmoji, discord.Reaction, str]):
        """ Add the given emojis as a reaction to the specified message. """

        for emoji in emojis:
            try:
                await message.add_reaction(emoji)
                await ctx.message.delete()
            except discord.errors.HTTPException:
                pass

    @commands.has_role(config.role_staff)
    @commands.before_invoke(record_usage)
    @commands.comnmand(name="vote")
    async def vote(self, ctx, message: discord.Message = None):
        """ Add vote reactions to a message. """
        async def get_last_message(ctx):
            messages = await ctx.channel.history(limit=2).flatten()
            return messages[1]

        message = message or await get_last_message(ctx)
        try:
            await ctx.message.delete()
            await message.add_reaction(config.emote_yes)
            await message.add_reaction(config.emote_no)
        except Exception as error:
            logging.error(error)
            pass

def setup(bot: Bot) -> None:
    """ Load the General cog. """
    bot.add_cog(General(bot))
    log.info("Commands loaded: general")
