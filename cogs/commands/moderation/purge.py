import logging

from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from cogs.commands import settings
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class PurgeCog(Cog):
    """ Purge Cog """

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def can_purge_messages(ctx: SlashContext):
        # Implement override for the owner.
        if ctx.author_id == ctx.guild.owner.id:
            return True

        # Prevent mods from removing message in moderation categories
        if ctx.channel.category_id in [settings.get_value("category_moderation"), settings.get_value("category_development"), settings.get_value("category_logs"), settings.get_value("category_tickets")]:
            await embeds.error_message(ctx=ctx, description="You cannot use that command in this category.")
            return False

        # Otherwise, the purge is fine to execute
        return True

    @commands.bot_has_permissions(manage_messages=True, send_messages=True, read_message_history=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="purge",
        description="Purges the last X amount of messages",
        guild_ids=[settings.get_value("guild_id")],
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
                required=False
            ),
        ],
        default_permission=False,
        permissions={
            settings.get_value("guild_id"): [
                create_permission(settings.get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
                create_permission(settings.get_value("role_trial_mod"), SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def remove_messages(self, ctx: SlashContext, amount: int, reason: str = None):
        """ Scans the number of messages and removes all that match specified members, if none given, remove all. """
        await ctx.defer()

        # Check to see if the bot is allowed to purge
        if not await self.can_purge_messages(ctx):
            return

        # Handle cases where the reason is not provided.
        if not reason:
            reason = "No reason provided."
        elif len(reason) > 512:
            await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")
            return

        # Limit the command at 100 messages maximum to avoid abuse.
        if amount > 100:
            amount = 100

        message = "messages"
        if amount == 1:
            message = message[:-1]

        await ctx.channel.purge(limit=amount + 1)

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Removed messages",
            description=f"{ctx.author.mention} removed the previous {amount} {message}.",
            thumbnail_url="https://i.imgur.com/EDy6jCp.png",
            color="soft_red"
        )
        embed.add_field(name="Reason:", value=reason, inline=False)
        # Do not use ctx.send(). See: https://discord-py-slash-command.readthedocs.io/en/latest/faq.html#what-is-the-difference-between-ctx-send-and-ctx-channel-send
        await ctx.channel.send(embed=embed)


def setup(bot: Bot) -> None:
    """ Load the Purge cog. """
    bot.add_cog(PurgeCog(bot))
    log.info("Commands loaded: purge")
