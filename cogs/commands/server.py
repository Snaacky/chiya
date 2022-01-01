import logging

import discord
from discord.commands import SlashCommandGroup, context, permissions
from discord.ext import commands

from utils import embeds
from utils.config import config


log = logging.getLogger(__name__)


class ServerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Permission type 1 is role and type 2 is user.
    server = SlashCommandGroup(
        "server",
        "Server management commands",
        guild_ids=config["guild_ids"],
        default_permission=False,
        permissions=[permissions.Permission(id=config["roles"]["staff"], type=1, permission=True)],
    )

    @server.command(name="pop", description="Gets the current server population")
    async def pop(self, ctx: context.ApplicationContext) -> None:
        """
        Send the current member count of the server.
        """
        await ctx.defer()
        await ctx.send_followup(ctx.guild.member_count)

    @server.command(name="boosters", description="List all the server boosters")
    async def boosters(self, ctx: context.ApplicationContext) -> None:
        """Send an embed with all current server boosters."""
        await ctx.defer()

        embed = embeds.make_embed(
            title=f"Total boosts: {ctx.guild.premium_subscription_count}",
            description="\n".join(user.mention for user in ctx.guild.premium_subscribers),
            thumbnail_url="https://i.imgur.com/22ZZG7h.png",
            footer=f"Total boosters: {len(ctx.guild.premium_subscribers)}",
            color=discord.Color.nitro_pink(),
        )
        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ServerCommands(bot))
    log.info("Commands loaded: server")
