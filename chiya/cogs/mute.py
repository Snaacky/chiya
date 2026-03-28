import discord
from discord import app_commands
from discord.ext import commands
from pytimeparse2 import parse

from chiya import db
from chiya.config import config
from chiya.models import ModLog
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member, log_embed_to_channel


class MuteCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mute", description="Mutes a user in the server")
    @app_commands.guilds(config.guild_id)
    @app_commands.describe(user="The user that will be muted")
    @app_commands.describe(reason="The reason why the user is being muted")
    @app_commands.describe(duration="The length of time the user will be muted for")
    async def mute(
        self,
        ctx: discord.Interaction,
        user: discord.User | discord.Member,
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

        if not ctx.guild:
            return

        if not isinstance(user, discord.Member):
            return await embeds.send_error(ctx=ctx, description="That user is not in the server.")

        if not can_action_member(ctx=ctx, member=user):
            return await embeds.send_error(ctx=ctx, description=f"You cannot action {user.mention}.")

        if user.is_timed_out():
            return await embeds.send_error(ctx=ctx, description=f"{user.mention} is already muted.")

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        delta = parse(duration, as_timedelta=True)
        if not delta:
            return await embeds.send_error(ctx=ctx, description="Unable to decipher duration, please try again")

        muted_until = ctx.created_at + delta
        if delta.days >= 7:
            return await embeds.send_error(ctx=ctx, description="Timeout duration cannot exceed 7 days.")

        mod_embed = discord.Embed()
        mod_embed.title = "Muted member"
        mod_embed.description = f"{user.mention} was muted by {ctx.user.mention} for: {reason}"
        mod_embed.color = 0xCD6D6D
        mod_embed.add_field(name="Expires:", value=f"<t:{int(muted_until.timestamp())}:R>", inline=True)
        mod_embed.add_field(name="Reason:", value=reason, inline=False)
        mod_embed.set_thumbnail(url="https://files.catbox.moe/6rs4fn.png")

        user_embed = discord.Embed()
        user_embed.title = "Uh-oh, you've been muted!"
        user_embed.description = "If you believe this was a mistake, contact staff."
        user_embed.color = discord.Color.blurple()
        user_embed.add_field(name="Server:", value=ctx.guild.name, inline=True)
        user_embed.add_field(name="Duration:", value=f"<t:{int(muted_until.timestamp())}:R>", inline=True)
        user_embed.add_field(name="Reason:", value=reason, inline=False)
        user_embed.set_image(url="https://files.catbox.moe/b05gg3.gif")

        try:
            await user.send(embed=user_embed)
        except discord.Forbidden, discord.HTTPException:
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        log = ModLog()
        log.user_id = user.id
        log.mod_id = ctx.user.id
        log.timestamp = int(ctx.created_at.timestamp())
        log.reason = reason
        log.duration = duration
        log.type = "mute"

        db.session.add(log)
        db.session.commit()

        await user.timeout(muted_until, reason=reason)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)

    @app_commands.command(name="unmute", description="Umutes a member in the server")
    @app_commands.guilds(config.guild_id)
    @app_commands.describe(user="The member that will be unmuted")
    @app_commands.describe(reason="The reason why the member is being unmuted")
    async def unmute(
        self,
        ctx: discord.Interaction,
        user: discord.User | discord.Member,
        reason: str,
    ) -> None:
        """
        Unmute the user, log the action to the database, and attempt to send
        them a direct message alerting them of their mute.

        If the user has privacy settings enabled or has the bot blocked they
        will be unable to receive the ban notification. The bot will let the
        invoking mod know if this is the case.

        TODO: Either setup a scheduler or check if an event is emitted when a
        mute expires so that we can return the same unmute embed when the user
        expires naturally.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not ctx.guild:
            return

        if not isinstance(user, discord.Member):
            return await embeds.send_error(ctx=ctx, description="That user is not in the server.")

        if not can_action_member(ctx=ctx, member=user):
            return await embeds.send_error(ctx=ctx, description=f"You cannot action {user.mention}.")

        if not user.is_timed_out():
            return await embeds.send_error(ctx=ctx, description=f"{user.mention} is not muted.")

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        mod_embed = discord.Embed()
        mod_embed.title = "Unmuted member"
        mod_embed.description = f"{user.mention} was unmuted by {ctx.user.mention}"
        mod_embed.color = discord.Color.green()
        mod_embed.add_field(name="Reason:", value=reason, inline=False)
        mod_embed.set_thumbnail(url="https://files.catbox.moe/izm83m.png")

        user_embed = discord.Embed()
        user_embed.title = "Yay, you've been unmuted!"
        user_embed.description = "Review our server rules to avoid being actioned again in the future."
        user_embed.color = discord.Color.blurple()
        user_embed.add_field(name="Server:", value=ctx.guild.name, inline=True)
        user_embed.add_field(name="Reason:", value=reason, inline=False)
        user_embed.set_image(url="https://files.catbox.moe/razmf6.gif")

        try:
            await user.send(embed=user_embed)
        except discord.Forbidden, discord.HTTPException:
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        log = ModLog()
        log.user_id = user.id
        log.mod_id = ctx.user.id
        log.timestamp = int(ctx.created_at.timestamp())
        log.reason = reason
        log.type = "unmute"

        db.session.add(log)
        db.session.commit()

        await user.timeout(None, reason=reason)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """
        Add the user's mute entry to the database if they were timed out manually.
        """
        if before.timed_out_until is None and after.timed_out_until is None:
            return

        logs = [log async for log in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update)]
        if not logs or not logs[0].user or logs[0].user == self.bot.user:
            return

        if before.timed_out_until is None:
            seconds = round((logs[0].after.timed_out_until - logs[0].created_at).total_seconds())
            duration = {
                60: "60 seconds",
                300: "5 minutes",
                600: "10 minutes",
                3600: "1 hour",
                86400: "1 day",
                604800: "1 week",
            }.get(seconds, f"{seconds} seconds")

            new = ModLog()
            new.user_id = after.id
            new.mod_id = logs[0].user.id
            new.timestamp = int(logs[0].created_at.timestamp())
            new.reason = logs[0].reason or "*User was manually muted, no reason provided.*"
            new.duration = duration
            new.type = "mute"

        else:
            new = ModLog()
            new.user_id = after.id
            new.mod_id = logs[0].user.id
            new.timestamp = int(logs[0].created_at.timestamp())
            new.reason = logs[0].reason or "*User was manually unmuted, no reason provided.*"
            new.type = "unmute"

        db.session.add(new)
        db.session.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MuteCog(bot))
