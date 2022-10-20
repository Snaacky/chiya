import logging
import time
from datetime import datetime, timezone

import discord
from discord.commands import Option, context, slash_command
from discord.ext import commands

from chiya import config, database
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member, get_duration


log = logging.getLogger(__name__)


class MuteCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @slash_command(guild_ids=config["guild_ids"], description="Mutes a member in the server")
    @commands.has_any_role(config["roles"]["staff"], config["roles"]["chat_mod"])
    async def mute(
        self,
        ctx: context.ApplicationContext,
        member: Option(discord.Member | discord.User, description="The member that will be muted", required=True),
        reason: Option(str, description="The reason why the member is being muted", required=True),
        duration: Option(str, description="The length of time the user will be muted for", required=True),
    ) -> None:
        """
        Mute the user, log the action to the database, and attempt to send
        them a direct message alerting them of their mute.

        If the user isn't in the server, has privacy settings enabled,
        or has the bot blocked they will be unable to receive the ban
        notification. The bot will let the invoking mod know if this
        is the case.
        """
        await ctx.defer()

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        if member.timed_out:
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

        mute_embed = embeds.make_embed(
            ctx=ctx,
            title=f"Muting member: {member}",
            description=f"{member.mention} was muted by {ctx.author.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/rHtYWIt.png",
            color=discord.Color.red(),
            fields=[{"name": "Duration:", "value": duration_string, "inline": False}],
        )

        dm_embed = embeds.make_embed(
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
            await member.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            mute_embed.add_field(
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
                mod_id=ctx.author.id,
                timestamp=int(time.time()),
                reason=reason,
                duration=duration_string,
                type="mute",
            )
        )
        db.commit()
        db.close()

        await member.timeout(until=datetime.utcfromtimestamp(mute_end_time), reason=reason)
        await ctx.send_followup(embed=mute_embed)

    @slash_command(guild_ids=config["guild_ids"], description="Unmute a member in the server")
    @commands.has_role(config["roles"]["staff"])
    async def unmute(
        self,
        ctx: context.ApplicationContext,
        member: Option(discord.Member | discord.User, description="The member that will be unmuted", required=True),
        reason: Option(str, description="The reason why the member is being unmuted", required=True),
    ) -> None:
        """
        Unmute the user, log the action to the database, and attempt to send
        them a direct message alerting them of their mute.

        If the user has privacy settings enabled or has the bot blocked they
        will be unable to receive the ban notification. The bot will let the
        invoking mod know if this is the case.
        """
        await ctx.defer()

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        if not member.timed_out:
            return await embeds.error_message(ctx=ctx, description=f"{member.mention} is not muted.")

        if len(reason) > 1024:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 1024 characters.")

        unmute_embed = embeds.make_embed(
            ctx=ctx,
            title=f"Unmuting member: {member.name}",
            description=f"{member.mention} was unmuted by {ctx.author.mention} for: {reason}",
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7DpUHC.png",
        )

        dm_embed = embeds.make_embed(
            author=False,
            title="Yay, you've been unmuted!",
            description="Review our server rules to avoid being actioned again in the future.",
            image_url="https://i.imgur.com/U5Fvr2Y.gif",
            color=discord.Color.blurple(),
            fields=[
                {"name": "Server:", "value": f"[{ctx.guild.name}]({await ctx.guild.vanity_invite()})", "inline": True},
                {"name": "Moderator:", "value": ctx.author.mention, "inline": True},
                {"name": "Reason:", "value": reason, "inline": False},
            ],
        )
        try:
            await member.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            unmute_embed.add_field(
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
                mod_id=ctx.author.id,
                timestamp=int(time.time()),
                reason=reason,
                type="unmute",
            )
        )
        db.commit()
        db.close()

        await member.remove_timeout(reason=reason)
        await ctx.send_followup(embed=unmute_embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(MuteCommands(bot))
    log.info("Commands loaded: mute")
