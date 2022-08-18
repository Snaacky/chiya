import logging

import discord
from discord.commands import SlashCommandGroup, context
from discord.ext import commands

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class ServerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Permission type 1 is role and type 2 is user.
    server = SlashCommandGroup(
        name="server",
        description="Server management commands",
        guild_ids=config["guild_ids"],
    )

    @server.command(name="pop", description="Gets the current server population")
    @commands.has_role(config["roles"]["staff"])
    async def pop(self, ctx: context.ApplicationContext) -> None:
        """
        Send the current member count of the server.
        """
        await ctx.defer()
        await ctx.send_followup(ctx.guild.member_count)

    @server.command(name="boosters", description="List all the server boosters")
    @commands.has_role(config["roles"]["staff"])
    async def boosters(self, ctx: context.ApplicationContext) -> None:
        """
        Send an embed with all current server boosters.
        """
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
