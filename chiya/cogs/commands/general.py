import logging

import discord
from discord import app_commands
from discord.ext import commands

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class GeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="pfp", description="Gets a users profile picture")
    @app_commands.guilds(config["guild_id"])
    @app_commands.describe(user="User whose profile picture will be grabbed")
    @app_commands.describe(profile="Prefer global profile picture")
    async def pfp(
        self,
        ctx: discord.Interaction,
        user: discord.Member | discord.User = None,
        profile: bool = None
    ) -> None:
        """Send an embed with the specified users avatar."""
        await ctx.response.defer(thinking=True, ephemeral=True)
        user = user or ctx.user
        embed = embeds.make_embed()
        if profile and isinstance(user, discord.Member):
            user: discord.User = ctx.client.get_user(user.id)
        embed.set_author(icon_url=user.display_avatar.url, name=str(user))
        embed.set_image(url=user.display_avatar.url)
        await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GeneralCommands(bot))
    log.info("Commands loaded: general")
