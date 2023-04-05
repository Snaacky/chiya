import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger as log

from chiya import config
from chiya.utils import embeds


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
        """
        Grab a user's avatar and return it in a large-sized embed.

        If the user parameter is not specified, the function will grab the
        invokers avatar instead. Offers the ability to attempt to grab a users
        server avatar and will fallback to their global avatar with a warning
        attached if a server specific avatar is not set.
        """
        await ctx.response.defer(thinking=True)
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
