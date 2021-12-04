import logging

import discord
from discord.commands import Option, context, permissions, slash_command
from discord.ext import commands
from utils import embeds
from utils.config import config

log = logging.getLogger(__name__)


class PurgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def can_purge_messages(self, ctx: context.ApplicationContext):
        """
        Checks if messages can be purged based on the context.

        Args:
            ctx (): The context of the slash command.

        Returns:
            True if able to purge, False otherwise.
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
        guild_id=config["guild_id"],
        default_permission=False,
        description="Purges the last X amount of messages",
    )
    @permissions.has_role(config["roles"]["privileged"]["staff"])
    async def purge(
        self,
        ctx: context.ApplicationContext,
        amount: Option(
            int,
            description="The amount of messages to be purged (100 message maximum cap)",
            required=True,
        ),
        reason: Option(
            str,
            description="The reason why the messages are being purged",
            required=True,
        ),
    ):
        """
        Slash command for purging messages from a channel.

        Args:
            ctx (): The context of the slash command.
            amount (): The number of messages to purge.
            reason (): The reason provided by the staff member issuing the purge.

        Notes:
            - The upper limit for amount is 100 messages and any attempts to use a
            higher number will be capped down to 100.
            - Uses bulk=True to delete messages faster in one sweep at the cost of
            being unable to delete messages older than 2 weeks.
        """

        await ctx.defer()

        if not await self.can_purge_messages(ctx):
            return await embeds.error_message(
                ctx=ctx, description="You cannot use that command in this category."
            )

        if len(reason) > 512:
            return await embeds.error_message(
                ctx=ctx, description="Reason must be less than 512 characters."
            )

        amount = 100 if amount > 100 else amount

        await ctx.channel.purge(
            limit=amount, before=ctx.channel.last_message.created_at, bulk=True
        )
        embed = embeds.make_embed(
            ctx=ctx,
            title="Purged messages",
            description=f"{ctx.author.mention} purged {amount} {'message' if amount == 1 else 'messages'}.",
            thumbnail_url="https://i.imgur.com/EDy6jCp.png",
            color="soft_red",
        )
        embed.add_field(name="Reason:", value=reason, inline=False)
        await ctx.send(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(PurgeCog(bot))
    log.info("Commands loaded: purge")
