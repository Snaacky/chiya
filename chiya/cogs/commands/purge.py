import logging

import discord
from discord import app_commands
from discord.ext import commands

from chiya import config
from chiya.utils import embeds
from chiya.utils.helpers import log_embed_to_channel


log = logging.getLogger(__name__)


class PurgeCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def can_purge_messages(self, ctx: discord.Interaction) -> bool:
        """
        Check used by purge function to make sure that the moderation,
        development, logs, and tickets categories can't be purged for
        security reasons.
        """
        if ctx.user.id == ctx.guild.owner.id:
            return True

        if ctx.channel.category_id in [
            config["categories"]["moderation"],
            config["categories"]["development"],
            config["categories"]["logs"],
            config["categories"]["tickets"],
        ]:
            return False

        return True

    @app_commands.command(name="purge", description="Purge the last X amount of messages")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.checks.has_role(config["roles"]["staff"])
    @app_commands.describe(amount="The amount of messages to be purged")
    @app_commands.describe(reason="The reason why the messages are being purged")
    async def purge(self, ctx: discord.Interaction, amount: int, reason: str) -> None:
        """
        Removes the last X amount of messages in bulk.

        Capped at a maximum of 100 messages per command invoke to avoid
        accidents wiping out large chunks of messages.

        Cannot be used in the moderation, development, logs, or archive
        categories for security reasons.
        """
        await ctx.response.defer(thinking=True)

        if not self.can_purge_messages(ctx):
            return await embeds.error_message(ctx=ctx, description="You cannot use that command in this category.")

        if len(reason) > 4096:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 4096 characters.")

        amount = 100 if amount > 100 else amount

        embed = embeds.make_embed(
            title="Purged messages",
            description=f"{ctx.user.mention} purged {amount} message(s) in {ctx.channel.mention}.",
            thumbnail_url="https://i.imgur.com/EDy6jCp.png",
            color=discord.Color.red(),
            fields=[{"name": "Reason:", "value": reason, "inline": False}],
        )
        await ctx.channel.purge(limit=amount, bulk=True)
        await ctx.followup.send(embed=embed)
        await log_embed_to_channel(ctx=ctx, embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PurgeCommands(bot))
    log.info("Commands loaded: purge")
