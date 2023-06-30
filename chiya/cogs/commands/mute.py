import time
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord import app_commands
from loguru import logger as log

from chiya import database
from chiya.config import config
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member, get_duration, log_embed_to_channel


class MuteCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mute", description="Mutes a member in the server")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.describe(member="The member that will be muted")
    @app_commands.describe(reason="The reason why the member is being muted")
    @app_commands.describe(duration="The length of time the user will be muted for")
    async def mute(
        self,
        ctx: discord.Interaction,
        member: discord.Member | discord.User,
        reason: str,
        duration: str,
    ) -> None:
        """
        Mute the user, log the action to the database, and attempt to send
        them a direct message alerting them of their mute.

        If the user isn't in the server, has privacy settings enabled,
        or has the bot blocked they will be unable to receive the ban
        notification. The bot will let the invoking mod know if this
        is the case.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        if member.is_timed_out():
            return await embeds.error_message(ctx=ctx, description=f"{member.mention} is already muted.")

        if len(reason) > 1024:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 1024 characters.")

        duration_string, mute_end_time = get_duration(duration=duration)
        if not duration_string:
            return await embeds.error_message(
                ctx=ctx,
                description=(
                    "Duration syntax: `y#mo#w#d#h#m#s` (year, month, week, day, hour, min, sec)\n"
                    "You can specify up to all seven but you only need one."
                ),
            )

        time_delta = mute_end_time - datetime.now(tz=timezone.utc).timestamp()

        if time_delta >= 2419200:
            return await embeds.error_message(ctx=ctx, description="Timeout duration cannot exceed 28 days.")

        mod_embed = embeds.make_embed(
            ctx=ctx,
            title=f"Muting member: {member}",
            description=f"{member.mention} was muted by {ctx.user.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/rHtYWIt.png",
            color=discord.Color.red(),
            fields=[{"name": "Duration:", "value": duration_string, "inline": False}],
        )

        user_embed = embeds.make_embed(
            title="Uh-oh, you've been muted!",
            description="If you believe this was a mistake, contact staff.",
            image_url="https://i.imgur.com/840Q48l.gif",
            color=discord.Color.blurple(),
            fields=[
                {"name": "Server:", "value": f"[{ctx.guild.name}]({await ctx.guild.vanity_invite()})", "inline": True},
                {"name": "Duration:", "value": duration_string, "inline": True},
                {"name": "Reason:", "value": reason, "inline": False},
            ],
        )

        try:
            await member.send(embed=user_embed)
        except (discord.Forbidden, discord.HTTPException):
            mod_embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                ),
            )

        db = database.Database().get()
        db["mod_logs"].insert(
            dict(
                user_id=member.id,
                mod_id=ctx.user.id,
                timestamp=int(time.time()),
                reason=reason,
                duration=duration_string,
                type="mute",
            )
        )
        db.commit()
        db.close()

        await member.timeout(datetime.fromtimestamp(mute_end_time, timezone.utc), reason=reason)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)

    @app_commands.command(name="unmute", description="Umutes a member in the server")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.describe(member="The member that will be unmuted")
    @app_commands.describe(reason="The reason why the member is being unmuted")
    async def unmute(
        self,
        ctx: discord.Interaction,
        member: discord.Member | discord.User,
        reason: str,
    ) -> None:
        """
        Unmute the user, log the action to the database, and attempt to send
        them a direct message alerting them of their mute.

        If the user has privacy settings enabled or has the bot blocked they
        will be unable to receive the ban notification. The bot will let the
        invoking mod know if this is the case.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        if not member.is_timed_out():
            return await embeds.error_message(ctx=ctx, description=f"{member.mention} is not muted.")

        if len(reason) > 1024:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 1024 characters.")

        mod_embed = embeds.make_embed(
            ctx=ctx,
            title=f"Unmuting member: {member.name}",
            description=f"{member.mention} was unmuted by {ctx.user.mention} for: {reason}",
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7DpUHC.png",
        )

        user_embed = embeds.make_embed(
            author=False,
            title="Yay, you've been unmuted!",
            description="Review our server rules to avoid being actioned again in the future.",
            image_url="https://i.imgur.com/U5Fvr2Y.gif",
            color=discord.Color.blurple(),
            fields=[
                {"name": "Server:", "value": f"[{ctx.guild.name}]({await ctx.guild.vanity_invite()})", "inline": True},
                {"name": "Reason:", "value": reason, "inline": False},
            ],
        )
        try:
            await member.send(embed=user_embed)
        except (discord.Forbidden, discord.HTTPException):
            mod_embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                ),
            )

        db = database.Database().get()
        db["mod_logs"].insert(
            dict(
                user_id=member.id,
                mod_id=ctx.user.id,
                timestamp=int(time.time()),
                reason=reason,
                type="unmute",
            )
        )
        db.commit()
        db.close()

        await member.timeout(None, reason=reason)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MuteCommands(bot))
    log.info("Commands loaded: mute")
