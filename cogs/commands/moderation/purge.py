import logging

from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_permission
from discord_slash.model import SlashCommandPermissionType

import config
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)

class PurgeCog(Cog):
    """ Purge Cog """

    def __init__(self, bot):
        self.bot = bot

    async def can_purge_messages(self, ctx: SlashContext):
        # Implement override for the owner.
        if ctx.author_id == ctx.guild.owner.id:
            return True

        # Prevent mods from removing message in moderation categories
        if ctx.channel.category_id in [config.moderation_category, config.development_category, config.logs_category, config.tickets_category]:
            await embeds.error_message(ctx=ctx, description="You cannot use that command in this category.")
            return False

        # Otherwise, the purge is fine to execute
        return True
        
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, read_message_history=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="purge", 
        description="Purges the last X amount of messages",
        guild_ids=[622243127435984927],
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
            622243127435984927: [
                create_permission(763031634379276308, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def remove_messages(self, ctx: SlashContext, number_of_messages: int, reason: str = None):
        """ Scans the number of messages and removes all that match specified members, if none given, remove all. """
        
        # Check to see if the bot is allowed to purge
        if not await self.can_purge_messages(ctx):
            return

        # Limit the command at 100 messages maximum to avoid abuse.
        if number_of_messages > 100:
            number_of_messages = 100

        # Handle cases where the reason is not provided.
        if not reason:
            reason = "No reason provided."

        if len(reason) > 512:
            await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")
            return

        embed = embeds.make_embed(
            ctx=ctx, 
            title=f"Removed messages", 
            thumbnail_url=config.message_delete, 
            color="soft_red"
        )

        deleted = await ctx.channel.purge(limit=number_of_messages)
        embed.description=f"{ctx.author.mention} removed the previous {len(deleted)} messages."
        embed.add_field(name="Reason:", value=reason, inline=False)
        await ctx.send(embed=embed)

def setup(bot: Bot) -> None:
    """ Load the Purge cog. """
    bot.add_cog(PurgeCog(bot))
    log.info("Commands loaded: purge")
