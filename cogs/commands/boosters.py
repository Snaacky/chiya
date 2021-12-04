import logging

import discord
from discord.commands import context, permissions, slash_command
from discord.ext import commands

from utils.config import config
from utils import embeds


log = logging.getLogger(__name__)


class Boosters(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_id=config["guild_id"], default_permission=False, description="List all the server boosters")
    @permissions.has_role(config["roles"]["privileged"]["staff"])
    async def boosters(self, ctx: context.ApplicationContext):
        """
        Slash command for getting the current list of server boosters.

        Args:
            ctx (Context): The context of the slash command.
        """
        await ctx.defer()

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Total boosts: {ctx.guild.premium_subscription_count}",
            thumbnail_url="https://i.imgur.com/22ZZG7h.png",
            color="nitro_pink",
            author=False
        )
        embed.description = "\n".join(user.mention for user in ctx.guild.premium_subscribers)
        embed.set_footer(text=f"Total boosters: {len(ctx.guild.premium_subscribers)}")
        await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(Boosters(bot))
    log.info("Commands loaded: boosters")
