import logging
import time

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, Greedy

import config
from utils import database
from utils import embeds
from utils.record import record_usage

class BoostersNPCog(Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="boosters", aliases=['boosts'])
    async def send(self, ctx: Context):
        """ Sends a list of users boosting the server. """

        embed = embeds.make_embed(ctx=ctx, title=f"Total boosts: {ctx.guild.premium_subscription_count}", 
            image_url=config.nitro, color="nitro_pink", author=False)
        descstring = "\n".join(str("<@" + str(subuser.id) + ">") for subuser in ctx.guild.premium_subscribers)
        embed.set_footer(text="Total boosters: " + str(len(ctx.guild.premium_subscribers)))
        embed.description=descstring
        await ctx.reply(embed=embed)


def setup(bot: Bot) -> None:
    """ Load the BoosterNPCog cog. """
    bot.add_cog(BoostersNPCog(bot))