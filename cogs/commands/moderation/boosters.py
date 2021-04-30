from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context

import config
from utils import embeds
from utils.record import record_usage

class BoostersCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="boosters", aliases=['boosts'])
    async def send_boosters_list(self, ctx: Context):
        """ Sends a list of users boosting the server. """

        embed = embeds.make_embed(ctx=ctx, title=f"Total boosts: {ctx.guild.premium_subscription_count}", 
            image_url=config.nitro, color="nitro_pink", author=False)
        description = "\n".join(f"{user.mention}" for user in ctx.guild.premium_subscribers)
        embed.set_footer(text=f"Total boosters: {len(ctx.guild.premium_subscribers)}")
        embed.description=description
        await ctx.reply(embed=embed)

def setup(bot: Bot) -> None:
    """ Load the BoosterCog cog. """
    bot.add_cog(BoostersCog(bot))