import asyncio
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

    @commands.has_role(config.role_staff)
    @commands.command(aliases=["population", "pop"])
    async def count(self, ctx):
        """Returns the current guild member count."""
        await ctx.send(ctx.guild.member_count)

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
        
    @commands.bot_has_permissions(read_message_history=True, add_reactions=True)
    @commands.before_invoke(record_usage)
    @commands.command(name='testing')
    async def testing(self, ctx, id):
        ticket = discord.utils.get(discord.utils.get(ctx.guild.categories, 
                                id=config.ticket_category_id).text_channels, 
                                name=f"ticket-123949837791002625")
        messages = await ticket.history().flatten()

        for message in messages[::-1]:
            await ctx.reply(message)
            await asyncio.sleep(2)

    @commands.bot_has_permissions(read_message_history=True, add_reactions=True)
    @commands.before_invoke(record_usage)
    @commands.command(name='testing2')
    async def testing2(self, ctx):
        general = discord.utils.get(ctx.guild.channels, id=631919775613845504)
        boost_id = 831964491662622730
        test = await general.fetch_message(boost_id)
        
        if test.type.value == 8:
            await ctx.reply(test.author.mention)








def setup(bot: Bot) -> None:
    """ Load the General cog. """
    bot.add_cog(General(bot))
    log.info("Cog loaded: General")
