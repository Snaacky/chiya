import logging

from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from utils import embeds
from utils.config import config
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
        if ctx.author_id == ctx.guild.owner.id: return True

        # Prevent mods from removing message in moderation categories
        if ctx.channel.category_id in [
                config["categories"]["moderation"], 
                config["categories"]["development"],
                config["categories"]["logs"],
                config["categories"]["tickets"]
            ]:
            await embeds.error_message(ctx=ctx, description="You cannot use that command in this category.")
            return False

        # Otherwise, the purge is fine to execute
        return True

    @commands.bot_has_permissions(manage_messages=True, send_messages=True, read_message_history=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="purge",
        description="Purges the last X amount of messages",
        guild_ids=config["guild_ids"],
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
            config["guild_ids"][0]: [
                create_permission(config["roles"]["staff"], SlashCommandPermissionType.ROLE, True),
                create_permission(config["roles"]["trial_mod"], SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def remove_messages(self, ctx: SlashContext, amount: int, reason: str = None):
        """ Scans the number of messages and removes all that match specified members, if none given, remove all. """
        # Defer the response because Discord API can sometimes be too slow.
        await ctx.defer()

        # Check to see if the bot is allowed to purge the messages.
        if not await self.can_purge_messages(ctx): return

        # Limit the reason parameter to 512 characters.
        if reason and len(reason) > 512:
            await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")
            return

        # Limit the command at 100 messages maximum to avoid abuse.
        amount = 100 if amount > 100 else amount

        # Purge the amount of messages before the command invoke.
        await ctx.channel.purge(limit=amount, before=ctx.created_at, bulk=True)

        # Generate the return embed.
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Purged messages",
            description=f"{ctx.author.mention} purged {amount} {'message' if amount == 1 else 'messages'}.",
            thumbnail_url="https://i.imgur.com/EDy6jCp.png",
            color="soft_red"
        )

        # Only add the field to the embed if the reason was set.
        if reason:
            embed.add_field(name="Reason:", value=reason, inline=False)

        # Send the embed (and also end the defer).
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    """ Load the Purge cog. """
    bot.add_cog(PurgeCog(bot))
    log.info("Commands loaded: purge")
