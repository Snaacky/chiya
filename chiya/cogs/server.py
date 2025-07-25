import discord
from discord import app_commands
from discord.ext import commands

from chiya.config import config
from chiya.utils import embeds


class ServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.checks.has_role(config.roles.staff)
    class ServerGroup(app_commands.Group):
        pass

    server = ServerGroup(name="server", guild_ids=[config.guild_id])

    @server.command(name="pop", description="Gets the current server population")
    async def pop(self, ctx: discord.Interaction) -> None:
        """Send a message with the current guild member count."""
        await ctx.response.defer(thinking=True)
        await ctx.followup.send(ctx.guild.member_count)

    @server.command(name="boosters", description="List all the server boosters")
    async def boosters(self, ctx: discord.Interaction) -> None:
        """Send an embed listing all the current server boosters."""
        await ctx.response.defer(thinking=True, ephemeral=True)

        embed = embeds.make_embed(
            title=f"Total boosts: {ctx.guild.premium_subscription_count}",
            description="\n".join(user.mention for user in ctx.guild.premium_subscribers),
            thumbnail_url="https://i.imgur.com/22ZZG7h.png",
            footer=f"Total boosters: {len(ctx.guild.premium_subscribers)}",
            color=discord.Color(0xF47FFF),
        )
        await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerCog(bot))
