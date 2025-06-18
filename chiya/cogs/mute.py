import arrow
import discord
from discord import app_commands
from discord.ext import commands
from parsedatetime import Calendar

from chiya.config import config
from chiya.models import ModLog
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member, log_embed_to_channel


class MuteCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mute", description="Mutes a member in the server")
    @app_commands.guilds(config.guild_id)
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
            return await embeds.send_error(ctx=ctx, description="That user is not in the server.")

        if not can_action_member(ctx=ctx, member=member):
            return await embeds.send_error(ctx=ctx, description=f"You cannot action {member.mention}.")

        if member.is_timed_out():
            return await embeds.send_error(ctx=ctx, description=f"{member.mention} is already muted.")

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        struct, status = Calendar().parse(duration)
        if not status:
            return await embeds.send_error(ctx=ctx, description="Unable to decipher duration, please try again")

        # arrow will assume the struct is in UTC unless we manually set the timezone to the system timezone
        # and then convert it to UTC afterwards. We shouldn't need to do this again unless using parsedatetime.
        muted_until = arrow.get(*struct[:6]).replace(tzinfo=arrow.now().tzinfo).to("utc")
        if muted_until >= arrow.utcnow().shift(days=+28):
            return await embeds.send_error(ctx=ctx, description="Timeout duration cannot exceed 28 days.")

        mod_embed = embeds.make_embed(
            ctx=ctx,
            title="Muted member",
            description=f"{member.mention} was muted by {ctx.user.mention} for: {reason}",
            thumbnail_url="https://files.catbox.moe/6rs4fn.png",
            color=0xCD6D6D,
            fields=[
                {"name": "Expires:", "value": f"<t:{int(muted_until.int_timestamp)}:R>", "inline": True},
                {"name": "Reason:", "value": reason, "inline": False},
            ],
        )

        user_embed = embeds.make_embed(
            title="Uh-oh, you've been muted!",
            description="If you believe this was a mistake, contact staff.",
            image_url="https://files.catbox.moe/b05gg3.gif",
            color=discord.Color.blurple(),
            fields=[
                {"name": "Server:", "value": f"{ctx.guild.name}", "inline": True},
                {"name": "Duration:", "value": f"<t:{int(muted_until.int_timestamp)}:R>", "inline": True},
                {"name": "Reason:", "value": reason, "inline": False},
            ],
        )

        try:
            await member.send(embed=user_embed)
        except (discord.Forbidden, discord.HTTPException):
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        ModLog(
            user_id=member.id,
            mod_id=ctx.user.id,
            timestamp=arrow.utcnow().int_timestamp,
            reason=reason,
            duration=duration,
            type="mute",
        ).save()

        await member.timeout(muted_until.datetime, reason=reason)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)

    @app_commands.command(name="unmute", description="Umutes a member in the server")
    @app_commands.guilds(config.guild_id)
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
            return await embeds.send_error(ctx=ctx, description="That user is not in the server.")

        if not can_action_member(ctx=ctx, member=member):
            return await embeds.send_error(ctx=ctx, description=f"You cannot action {member.mention}.")

        if not member.is_timed_out():
            return await embeds.send_error(ctx=ctx, description=f"{member.mention} is not muted.")

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        mod_embed = embeds.make_embed(
            ctx=ctx,
            title="Unmuted member",
            description=f"{member.mention} was unmuted by {ctx.user.mention}",
            color=discord.Color.green(),
            thumbnail_url="https://files.catbox.moe/izm83m.png",
            fields=[
                {"name": "Reason:", "value": reason, "inline": False},
            ],
        )

        user_embed = embeds.make_embed(
            author=False,
            title="Yay, you've been unmuted!",
            description="Review our server rules to avoid being actioned again in the future.",
            image_url="https://files.catbox.moe/razmf6.gif",
            color=discord.Color.blurple(),
            fields=[
                {"name": "Server:", "value": ctx.guild.name, "inline": True},
                {"name": "Reason:", "value": reason, "inline": False},
            ],
        )
        try:
            await member.send(embed=user_embed)
        except (discord.Forbidden, discord.HTTPException):
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        ModLog(
            user_id=member.id,
            mod_id=ctx.user.id,
            timestamp=arrow.utcnow().int_timestamp,
            reason=reason,
            type="unmute",
        ).save()

        await member.timeout(None, reason=reason)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """
        Add the user's mute entry to the database if they were timed out manually.
        """
        # TODO: Emit an embed in #moderation when this happens
        if not before.timed_out_until and after.timed_out_until:
            logs = [log async for log in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update)]
            if logs[0].user != self.bot.user:
                # TODO: need to log duration here
                ModLog(
                    user_id=after.id,
                    mod_id=logs[0].user.id,
                    timestamp=arrow.utcnow().int_timestamp,
                    reason=logs[0].reason,
                    type="mute",
                ).save()

        if not after.timed_out_until and before.timed_out_until:
            logs = [log async for log in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update)]
            if logs[0].user != self.bot.user:
                ModLog(
                    user_id=after.id,
                    mod_id=logs[0].user.id,
                    timestamp=arrow.utcnow().int_timestamp,
                    reason=logs[0].reason,
                    type="unmute",
                )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MuteCog(bot))
