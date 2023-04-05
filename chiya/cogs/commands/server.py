import discord
from discord.ext import commands
from discord import app_commands
from loguru import logger as log

from chiya import config
from chiya.utils import embeds


class ServerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.checks.has_role(config["roles"]["staff"])
    class ServerGroup(app_commands.Group):
        pass
    server = ServerGroup(name="server", description="Server management commands", guild_ids=[config["guild_id"]])

    @server.command(name="pop", description="Gets the current server population")
    async def pop(self, ctx: discord.Interaction) -> None:
        """
        Send the current member count of the server.
        """
        await ctx.response.defer(thinking=True)
        await ctx.followup.send(ctx.guild.member_count)

    @server.command(name="boosters", description="List all the server boosters")
    async def boosters(self, ctx: discord.Interaction) -> None:
        """
        Send an embed with all current server boosters.
        """
        await ctx.response.defer(thinking=True)

        embed = embeds.make_embed(
            title=f"Total boosts: {ctx.guild.premium_subscription_count}",
            description="\n".join(user.mention for user in ctx.guild.premium_subscribers),
            thumbnail_url="https://i.imgur.com/22ZZG7h.png",
            footer=f"Total boosters: {len(ctx.guild.premium_subscribers)}",
            color=discord.Color(0xf47fff),
        )
        await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerCommands(bot))
    log.info("Commands loaded: server")
