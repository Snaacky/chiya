import datetime
import logging
import time

import discord
import utils.duration
from discord.commands import Option, context, permissions, slash_command
from discord.ext import commands
from utils import database, embeds
from utils.config import config
from utils.moderation import can_action_member

log = logging.getLogger(__name__)


class MuteCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def mute_member(
        self,
        ctx: context.ApplicationContext,
        member: discord.Member,
        reason: str,
        end_time: float,
    ) -> None:

        await member.timeout(
            until=datetime.datetime.utcfromtimestamp(end_time), reason=reason
        )

        # Open a connection to the database.
        db = database.Database().get()

        # Add the mute to the mod_log database.
        db["mod_logs"].insert(
            dict(
                user_id=member.id,
                mod_id=ctx.author.id,
                timestamp=int(time.time()),
                reason=reason,
                type="mute",
            )
        )

        # Commit the changes to the database.
        db.commit()
        db.close()

    async def unmute_member(
        self,
        member: discord.Member,
        reason: str,
        ctx: context.ApplicationContext = None,
    ) -> None:
        moderator = ctx.author if ctx else self.bot.user

        await member.remove_timeout(reason=reason)

        # Open a connection to the database.
        db = database.Database().get()

        # Add the unmute to the mod_log database.
        db["mod_logs"].insert(
            dict(
                user_id=member.id,
                mod_id=moderator.id,
                timestamp=int(time.time()),
                reason=reason,
                type="unmute",
            )
        )

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

    async def send_muted_dm_embed(
        self,
        ctx: context.ApplicationContext,
        member: discord.Member,
        reason: str = None,
        duration: str = None,
    ) -> bool:

        try:
            dm_channel = await member.create_dm()
            embed = embeds.make_embed(
                author=False,
                title="Uh-oh, you've been muted!",
                description="If you believe this was a mistake, contact staff.",
                color=0x8083B0,
            )
            embed.add_field(
                name="Server:",
                value=f"[{ctx.guild}](https://discord.gg/piracy)",
                inline=True,
            )
            embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            embed.add_field(name="Length:", value=duration, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/840Q48l.gif")
            return await dm_channel.send(embed=embed)
        except discord.HTTPException:
            return False

    async def send_unmuted_dm_embed(
        self,
        member: discord.Member,
        reason: str,
        ctx: context.ApplicationContext = None,
    ) -> bool:
        moderator = ctx.author if ctx else self.bot.user

        # Send member message telling them that they were unmuted and why.
        try:  # In case user has DMs blocked.
            channel = await member.create_dm()
            embed = embeds.make_embed(
                author=False,
                title="Yay, you've been unmuted!",
                description="Review our server rules to avoid being actioned again in the future.",
                color=0x8A3AC5,
            )
            embed.add_field(
                name="Server:",
                value="[/r/animepiracy](https://discord.gg/piracy)",
                inline=True,
            )
            embed.add_field(name="Moderator:", value=moderator.mention, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/U5Fvr2Y.gif")
            return await channel.send(embed=embed)
        except discord.HTTPException:
            return False

    @slash_command(
        guild_ids=config["guild_ids"],
        default_permission=False,
        description="Mutes a member in the server",
    )
    @permissions.has_role(config["roles"]["staff"])
    async def mute(
        self,
        ctx: context.ApplicationContext,
        member: Option(
            discord.Member, description="The member that will be kicked", required=True
        ),
        reason: Option(
            str, description="The reason why the member is being kicked", required=True
        ),
        duration: Option(
            str,
            description="The length of time the user will be muted for",
            required=True,
        ),
    ):
        """Mutes member in guild."""
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if not isinstance(member, discord.Member):
            return await embeds.error_message(
                ctx=ctx, description="That user is not in the server."
            )

        # Checks if invoker can action that member (self, bot, etc.)
        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(
                ctx=ctx, description=f"You cannot action {member.mention}."
            )

        # Check if the user is muted already.
        if member.timed_out:
            return await embeds.error_message(
                ctx=ctx, description=f"{member.mention} is already muted."
            )

        # Discord caps embed fields at a ridiculously low character limit, avoids problems with future embeds.
        if len(reason) > 512:
            return await embeds.error_message(
                ctx=ctx, description="Reason must be less than 512 characters."
            )

        # Get the duration string for embed and mute end time for the specified duration.
        duration_string, mute_end_time = utils.duration.get_duration(duration=duration)
        # If the duration string is empty due to Regex not matching anything, send and error embed and return.
        if not duration_string:
            return await embeds.error_message(
                ctx=ctx,
                description=(
                    "Duration syntax: `#d#h#m#s` (day, hour, min, sec)\n"
                    "You can specify up to all four but you only need one."
                ),
            )

        # Start creating the embed that will be used to alert the moderator that the user was successfully muted.
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Muting member: {member}",
            thumbnail_url="https://i.imgur.com/rHtYWIt.png",
            color="soft_red",
        )
        embed.description = (
            f"{member.mention} was muted by {ctx.author.mention} for: {reason}"
        )
        embed.add_field(name="Duration:", value=duration_string, inline=False)

        # Attempt to DM the user to let them know they were muted.
        if not await self.send_muted_dm_embed(
            ctx=ctx, member=member, reason=reason, duration=duration_string
        ):
            embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                ),
            )

        # Mutes the user and stores the log in the mod log
        await self.mute_member(
            ctx=ctx, member=member, reason=reason, end_time=mute_end_time
        )
        await ctx.send_followup(embed=embed)

    @slash_command(
        guild_ids=config["guild_ids"],
        default_permission=False,
        description="Unmutes a member in the server",
    )
    @permissions.has_role(config["roles"]["staff"])
    async def unmute(
        self,
        ctx: context.ApplicationContext,
        member: Option(
            discord.Member, description="The member that will be unmuted", required=True
        ),
        reason: Option(
            str, description="The reason why the member is being kicked", required=True
        ),
    ):
        """Unmutes member in guild."""
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if not isinstance(member, discord.Member):
            return await embeds.error_message(
                ctx=ctx, description="That user is not in the server."
            )

        # Checks if invoker can action that member (self, bot, etc.)
        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(
                ctx=ctx, description=f"You cannot action {member.mention}."
            )

        if not member.timed_out:
            return await embeds.error_message(
                ctx=ctx, description=f"{member.mention} is not muted."
            )

        # Discord caps embed fields at a ridiculously low character limit, avoids problems with future embeds.
        if len(reason) > 512:
            return await embeds.error_message(
                ctx=ctx, description="Reason must be less than 512 characters."
            )

        # Start creating the embed that will be used to alert the moderator that the user was successfully unmuted.
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Unmuting member: {member.name}",
            color="soft_green",
            thumbnail_url="https://i.imgur.com/W7DpUHC.png",
        )
        embed.description = (
            f"{member.mention} was unmuted by {ctx.author.mention} for: {reason}"
        )

        # Attempt to DM the user to let them and the mods know they were unmuted.
        if not await self.send_unmuted_dm_embed(ctx=ctx, member=member, reason=reason):
            embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                ),
            )

        await ctx.send_followup(embed=embed)
        await self.unmute_member(ctx=ctx, member=member, reason=reason)


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(MuteCommands(bot))
    log.info("Commands loaded: mute")
