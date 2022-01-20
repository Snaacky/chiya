import logging

import discord
from discord.commands import Option, context, permissions, slash_command
from discord.ext import commands

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class PurgeCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def can_purge_messages(self, ctx: context.ApplicationContext) -> bool:
        """
        Check used by purge function to make sure that the moderation,
        development, logs, and tickets categories can't be purged for
        security reasons.
        """
        if ctx.author.id == ctx.guild.owner.id:
            return True

        if ctx.channel.category_id in [
            config["categories"]["moderation"],
            config["categories"]["development"],
            config["categories"]["logs"],
            config["categories"]["tickets"],
        ]:
            return False

        return True

    @slash_command(
        guild_ids=config["guild_ids"], default_permission=False, description="Purge the last X amount of messages"
    )
    @permissions.has_role(config["roles"]["staff"])
    async def purge(
        self,
        ctx: context.ApplicationContext,
        amount: Option(int, description="The amount of messages to be purged", required=True),
        reason: Option(str, description="The reason why the messages are being purged", required=True),
    ) -> None:
        """
        Removes the last X amount of messages in bulk.

        Capped at a maximum of 100 messages per command invoke to avoid
        accidents wiping out large chunks of messages.

        Cannot be used in the moderation, development, logs, or archive
        categories for security reasons.
        """
        await ctx.defer()

        if not await self.can_purge_messages(ctx):
            return await embeds.error_message(ctx=ctx, description="You cannot use that command in this category.")

        if len(reason) > 4096:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 4096 characters.")

        amount = 100 if amount > 100 else amount

        embed = embeds.make_embed(
            title="Purged messages",
            description=f"{ctx.author.mention} purged {amount} {'message' if amount == 1 else 'messages'}.",
            thumbnail_url="https://i.imgur.com/EDy6jCp.png",
            color=discord.Color.red(),
            fields=[{"name": "Reason:", "value": reason, "inline": False}],
        )
        await ctx.channel.purge(limit=amount, before=ctx.channel.last_message.created_at, bulk=True)
        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(PurgeCommands(bot))
    log.info("Commands loaded: purge")
