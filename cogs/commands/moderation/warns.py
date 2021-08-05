import logging
import time

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from cogs.commands import settings
from utils import database
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class WarnsCog(Cog):
    """ Warns Cog """

    def __init__(self, bot):
        self.bot = bot

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="warn",
        description="Warn the member",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="member",
                description="The member that will be warned",
                option_type=6,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the member is being warned",
                option_type=3,
                required=True
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
    async def warn(self, ctx: SlashContext, member: discord.User, reason: str):
        """ Sends member a warning DM and logs to database. """
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if not isinstance(member, discord.Member):
            await embeds.error_message(ctx=ctx, description=f"That user is not in the server.")
            return

        if len(reason) > 512:
            await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")
            return

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Warning member: {member.name}",
            thumbnail_url="https://i.imgur.com/4jeFA3h.png",
            color="soft_orange"
        )

        embed.description = f"{member.mention} was warned by {ctx.author.mention} for: {reason}"

        # Send member message telling them that they were warned and why.
        try:  # In case user has DMs blocked.
            channel = await member.create_dm()
            warn_embed = embeds.make_embed(
                author=False,
                title=f"Uh-oh, you've received a warning!",
                description="If you believe this was a mistake, contact staff.",
                color=0xf7dcad
            )
            warn_embed.add_field(name="Server:", value=f"[{str(ctx.guild)}](https://discord.gg/piracy/)", inline=True)
            warn_embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            warn_embed.add_field(name="Reason:", value=reason, inline=False)
            warn_embed.set_image(url="https://i.imgur.com/rVf0mlG.gif")
            await channel.send(embed=warn_embed)
        except discord.HTTPException:
            embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. This can be caused by the user not being in the server, having DMs disabled, or having the bot blocked.")

        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        # Add the warning to the mod_log database.
        db["mod_logs"].insert(dict(
            user_id=member.id, 
            mod_id=ctx.author.id, 
            timestamp=int(time.time()), 
            reason=reason, 
            type="warn"
        ))

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    """ Load the Notes cog. """
    bot.add_cog(WarnsCog(bot))
    log.info("Commands loaded: warns")
