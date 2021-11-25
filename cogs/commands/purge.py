import logging

from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from utils import embeds
from utils.config import config


log = logging.getLogger(__name__)


class PurgeCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    async def can_purge_messages(self, ctx: SlashContext):
        """
        Checks if messages can be purged based on the context.

        Args:
            ctx (SlashContext): The context of the slash command.

        Returns:
            True if able to purge, False otherwise.
        """
        if ctx.author_id == ctx.guild.owner.id:
            return True

        if ctx.channel.category_id in [
                config["categories"]["moderation"],
                config["categories"]["development"],
                config["categories"]["logs"],
                config["categories"]["tickets"]]:
            return False

        return True

    @cog_ext.cog_slash(
        name="purge",
        description="Purges the last X amount of messages",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="amount",
                description="The amount of messages to be purged (100 message maximum cap)",
                option_type=4,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the messages are being purged",
                option_type=3,
                required=True
            ),
        ],
        default_permission=False,
        permissions={
            config["guild_id"]: [
                create_permission(config["roles"]["staff"], SlashCommandPermissionType.ROLE, True),
                create_permission(config["roles"]["trial_mod"], SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def purge(self, ctx: SlashContext, amount: int, reason: str):
        """
        Slash command for purging messages from a channel.

        Args:
            ctx (SlashContext): The context of the slash command.
            amount (int): The number of messages to purge.
            reason (str): The reason provided by the staff member issuing the purge.

        Notes:
            - The upper limit for amount is 100 messages and any attempts to use a
            higher number will be capped down to 100.
            - Uses bulk=True to delete messages faster in one sweep at the cost of
            being unable to delete messages older than 2 weeks.
        """

        await ctx.defer()

        if not await self.can_purge_messages(ctx):
            return await embeds.error_message(ctx=ctx, description="You cannot use that command in this category.")

        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        amount = 100 if amount > 100 else amount

        await ctx.channel.purge(limit=amount, before=ctx.created_at, bulk=True)
        embed = embeds.make_embed(
            ctx=ctx,
            title="Purged messages",
            description=f"{ctx.author.mention} purged {amount} {'message' if amount == 1 else 'messages'}.",
            thumbnail_url="https://i.imgur.com/EDy6jCp.png",
            color="soft_red"
        )
        embed.add_field(name="Reason:", value=reason, inline=False)
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(PurgeCog(bot))
    log.info("Commands loaded: purge")
