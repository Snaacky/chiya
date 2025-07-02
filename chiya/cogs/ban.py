import arrow

import discord
from discord import app_commands
from discord.ext import commands

from chiya.config import config
from chiya.models import ModLog
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member, log_embed_to_channel


class BanCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def is_user_banned(self, ctx: discord.Interaction, user: discord.Member | discord.User) -> bool:
        """Check if the user is banned from the context guild."""
        try:
            return bool(await self.bot.get_guild(ctx.guild.id).fetch_ban(user))
        except discord.NotFound:
            return False

    @app_commands.command(name="ban", description="Ban user from the server")
    @app_commands.guilds(config.guild_id)
    @app_commands.guild_only()
    @app_commands.describe(user="User to ban from the server")
    @app_commands.describe(reason="Reason why the user is being banned")
    @app_commands.describe(daystodelete="Days worth of messages to delete from the user, up to 7")
    async def ban(
        self,
        ctx: discord.Interaction,
        user: discord.Member | discord.User,
        reason: str,
        daystodelete: app_commands.Range[int, 1, 7] = None,
    ) -> None:
        """
        Ban the user, log the action to the database, and attempt to send them
        a direct message notfying them of their ban.

        If the user isn't in the server, has privacy settings enabled, or has
        the bot blocked they will be unable to receive the ban notification.
        The bot will let the invoking mod know if this is the case.

        daystodelete is limited to a maximum value of 7. This is a Discord API
        limitation with the .ban() function.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not can_action_member(ctx=ctx, member=user):
            return await embeds.send_error(ctx=ctx, description=f"You cannot action {user.mention}.")

        if await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.send_error(ctx=ctx, description=f"{user.mention} is already banned.")

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        mod_embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title=f"Banning user: {user}",
            description=f"{user.mention} was banned by {ctx.user.mention} for: {reason}",
            thumbnail_url="https://files.catbox.moe/6hd0uw.png",
            color=0xCD6D6D,
        )

        user_embed = embeds.make_embed(
            author=False,
            title="Uh-oh, you've been banned!",
            description=(
                "You can submit a ban appeal on our subreddit [here]"
                "(https://www.reddit.com/message/compose/?to=/r/snackbox)."
            ),
            image_url="https://files.catbox.moe/jp1wmf.gif",
            color=discord.Color.blurple(),
            fields=[
                {"name": "Server:", "value": ctx.guild.name, "inline": True},
                {"name": "Reason:", "value": reason, "inline": False},
            ],
        )

        try:
            await user.send(embed=user_embed)
        except (discord.Forbidden, discord.HTTPException):
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        ModLog(
            user_id=user.id,
            mod_id=ctx.user.id,
            timestamp=arrow.utcnow().int_timestamp,
            reason=reason,
            type="ban",
        ).save()

        await ctx.guild.ban(user=user, reason=reason, delete_message_days=daystodelete or 0)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)

    @app_commands.command(name="unban", description="Unban user from the server")
    @app_commands.guilds(config.guild_id)
    @app_commands.guild_only()
    @app_commands.describe(user="User to unban from the server")
    @app_commands.describe(reason="Reason why the user is being unbanned")
    async def unban(self, ctx: discord.Interaction, user: discord.Member | discord.User, reason: str) -> None:
        """
        Unban the user from the server and log the action to the database.

        Unlike when the user is banned, the bot is completely unable to let
        the user know that they were unbanned because it cannot communicate
        with users that it does not share a mutual server with.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.send_error(ctx=ctx, description=f"{user.mention} is not banned.")

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        mod_embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title=f"Unbanning user: {user}",
            description=f"{user.mention} was unbanned by {ctx.user.mention} for: {reason}",
            thumbnail_url="https://files.catbox.moe/qhc82k.png",
            color=discord.Color.green(),
        )

        ModLog(
            user_id=user.id,
            mod_id=ctx.user.id,
            timestamp=arrow.utcnow().int_timestamp,
            reason=reason,
            type="unban",
        ).save()

        await ctx.guild.unban(user, reason=reason)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.Member | discord.User) -> None:
        """
        Add the user's ban entry to the database if they were banned manually.
        """
        # TODO: Emit an embed in #moderation when this happens
        ban_entry = await guild.fetch_ban(user)
        logs = [log async for log in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban)]
        if logs[0].user != self.bot.user:
            ModLog(
                user_id=user.id,
                mod_log=logs[0].user.id,
                timestamp=arrow.utcnow().int_timestamp,
                reason=ban_entry.reason,
                type="ban",
            ).save()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BanCog(bot))
