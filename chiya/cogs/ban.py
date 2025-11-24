import arrow

import discord
from discord import app_commands
from discord.ext import commands

from chiya import db
from chiya.config import config
from chiya.models import ModLog
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member, log_embed_to_channel


class BanCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def is_user_banned(self, ctx: discord.Interaction, user: discord.User | discord.Member) -> bool:
        """Check if the user is banned from the context guild."""
        if not ctx.guild:
            return False

        try:
            return bool(await ctx.guild.fetch_ban(user))
        except discord.NotFound:
            return False

    @app_commands.command(name="ban", description="Ban user from the server")
    @app_commands.guilds(config.guild_id)
    @app_commands.describe(user="User to ban from the server")
    @app_commands.describe(reason="Reason why the user is being banned")
    @app_commands.describe(daystodelete="Days worth of messages to delete from the user, up to 7")
    async def ban(
        self,
        ctx: discord.Interaction,
        user: discord.User | discord.Member,
        reason: str,
        daystodelete: app_commands.Range[int, 1, 7] | None = None,
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

        if not ctx.guild:
            return

        if not can_action_member(ctx=ctx, member=user):
            return await embeds.send_error(ctx=ctx, description=f"You cannot action {user.mention}.")

        if await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.send_error(ctx=ctx, description=f"{user.mention} is already banned.")

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        mod_embed = discord.Embed()
        mod_embed.title = f"Banning user: {user}"
        mod_embed.description = f"{user.mention} was banned by {ctx.user.mention} for: {reason}"
        mod_embed.color = 0xCD6D6D
        mod_embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)
        mod_embed.set_thumbnail(url="https://files.catbox.moe/6hd0uw.png")

        user_embed = discord.Embed()
        user_embed.title = "Uh-oh, you've been banned!"
        user_embed.description = (
            "You can submit a ban appeal on our subreddit [here]"
            "(https://www.reddit.com/message/compose/?to=/r/snackbox)."
        )
        user_embed.color = discord.Color.blurple()
        user_embed.add_field(name="Server:", value=ctx.guild.name, inline=True)
        user_embed.add_field(name="Reason:", value=reason, inline=False)
        user_embed.set_image(url="https://files.catbox.moe/jp1wmf.gif")

        try:
            await user.send(embed=user_embed)
        except (discord.Forbidden, discord.HTTPException):
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        log = ModLog()
        log.user_id = user.id
        log.mod_id = ctx.user.id
        log.timestamp = arrow.utcnow().int_timestamp
        log.reason = reason
        log.type = "ban"

        db.session.add(log)
        db.session.commit()

        await ctx.guild.ban(user=user, reason=reason, delete_message_days=daystodelete or 0)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)

    @app_commands.command(name="unban", description="Unban user from the server")
    @app_commands.guilds(config.guild_id)
    @app_commands.describe(user="User to unban from the server")
    @app_commands.describe(reason="Reason why the user is being unbanned")
    async def unban(self, ctx: discord.Interaction, user: discord.User | discord.Member, reason: str) -> None:
        """
        Unban the user from the server and log the action to the database.

        Unlike when the user is banned, the bot is completely unable to let
        the user know that they were unbanned because it cannot communicate
        with users that it does not share a mutual server with.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not ctx.guild:
            return

        if not await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.send_error(ctx=ctx, description=f"{user.mention} is not banned.")

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        embed = discord.Embed()
        embed.title = f"Unbanning user: {user}"
        embed.description = f"{user.mention} was unbanned by {ctx.user.mention} for: {reason}"
        embed.color = discord.Color.green()
        embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)
        embed.set_thumbnail(url="https://files.catbox.moe/qhc82k.png")

        log = ModLog()
        log.user_id = user.id
        log.mod_id = ctx.user.id
        log.timestamp = arrow.utcnow().int_timestamp
        log.reason = reason
        log.type = "unban"

        db.session.add(log)
        db.session.commit()

        await ctx.guild.unban(user, reason=reason)
        await ctx.followup.send(embed=embed)
        await log_embed_to_channel(ctx=ctx, embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member) -> None:
        """
        Add the user's ban entry to the database if they were banned manually.
        """
        audit_log = await anext(guild.audit_logs(limit=1, action=discord.AuditLogAction.ban), None)
        if not audit_log or not audit_log.user or audit_log.user == self.bot.user:
            return

        # TODO: Emit an embed in #moderation when this happens
        ban_entry = await guild.fetch_ban(user)

        log = ModLog()
        log.user_id = user.id
        log.mod_id = audit_log.user.id
        log.timestamp = arrow.utcnow().int_timestamp
        log.type = "ban"
        log.reason = ban_entry.reason

        db.session.add(log)
        db.session.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BanCog(bot))
