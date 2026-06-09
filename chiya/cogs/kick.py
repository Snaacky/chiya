import discord
from discord import app_commands
from discord.ext import commands

from chiya import db
from chiya.config import config
from chiya.models import ModLog
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member, log_embed_to_channel


async def reasons(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    reasons = ("Compromised or hacked account", "Spam")
    return [app_commands.Choice(name=reason, value=reason) for reason in reasons if current.lower() in reason.lower()]


class KickCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.guilds(config.guild_id)
    @app_commands.describe(user="The member that will be kicked")
    @app_commands.describe(reason="The reason why the member is being kicked")
    @app_commands.autocomplete(reason=reasons)
    async def kick(self, ctx: discord.Interaction, user: discord.User | discord.Member, reason: str) -> None:
        """
        Kick the member, log the action to the database, and attempt to send
        them a direct message alerting them of the kick.

        If the member isn't in the server, has privacy settings enabled,
        or has the bot blocked they will be unable to receive the kick
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

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        mod_embed = discord.Embed()
        mod_embed.title = "Kicked member"
        mod_embed.description = f"{user.mention} was kicked by {ctx.user.mention}"
        mod_embed.color = 0xCD6D6D
        mod_embed.add_field(name="Reason:", value=reason, inline=False)
        mod_embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)
        mod_embed.set_thumbnail(url="https://files.catbox.moe/6hd0uw.png")

        user_embed = discord.Embed()
        user_embed.title = "Uh-oh, you've been kicked!"
        user_embed.description = "If you believe this was a mistake, contact staff."
        user_embed.color = discord.Color.blurple()
        user_embed.add_field(name="Server:", value=ctx.guild.name, inline=True)
        user_embed.add_field(name="Reason:", value=reason, inline=False)
        user_embed.set_image(url="https://files.catbox.moe/nyla1m.gif")

        try:
            await user.send(embed=user_embed)
        except discord.Forbidden, discord.HTTPException:
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        log = ModLog()
        log.user_id = user.id
        log.mod_id = ctx.user.id
        log.timestamp = int(ctx.created_at.timestamp())
        log.reason = reason
        log.type = "kick"

        db.session.add(log)
        db.session.commit()

        await user.kick(reason=reason)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)

    @app_commands.command(name="purgekick", description="Kick a member and delete their recent messages")
    @app_commands.guilds(config.guild_id)
    @app_commands.describe(user="The member that will be kicked")
    @app_commands.describe(reason="The reason why the member is being kicked")
    @app_commands.describe(daystodelete="Days worth of messages to delete from the member, up to 7")
    @app_commands.autocomplete(reason=reasons)
    async def purgekick(
        self,
        ctx: discord.Interaction,
        user: discord.User | discord.Member,
        reason: str,
        daystodelete: app_commands.Range[int, 1, 7] = 1,
    ) -> None:
        """
        Kick the member while deleting recent messages, log the action to the
        database, and attempt to send them a direct message alerting them of
        the kick.

        If the member isn't in the server, has privacy settings enabled,
        or has the bot blocked they will be unable to receive the kick
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

        if len(reason) > 1024:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 1024 characters.")

        deleted_messages = f"{daystodelete} day" if daystodelete == 1 else f"{daystodelete} days"

        mod_embed = discord.Embed()
        mod_embed.title = "Purge-kicked member"
        mod_embed.description = f"{user.mention} was purge-kicked by {ctx.user.mention}"
        mod_embed.color = 0xCD6D6D
        mod_embed.add_field(name="Deleted messages:", value=deleted_messages, inline=False)
        mod_embed.add_field(name="Reason:", value=reason, inline=False)
        mod_embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)
        mod_embed.set_thumbnail(url="https://files.catbox.moe/6hd0uw.png")

        user_embed = discord.Embed()
        user_embed.title = "Uh-oh, you've been kicked!"
        user_embed.description = "If you believe this was a mistake, contact staff."
        user_embed.color = discord.Color.blurple()
        user_embed.add_field(name="Server:", value=ctx.guild.name, inline=True)
        user_embed.add_field(name="Reason:", value=reason, inline=False)
        user_embed.set_image(url="https://files.catbox.moe/nyla1m.gif")

        try:
            await user.send(embed=user_embed)
        except discord.Forbidden, discord.HTTPException:
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        log = ModLog()
        log.user_id = user.id
        log.mod_id = ctx.user.id
        log.timestamp = int(ctx.created_at.timestamp())
        log.reason = reason
        log.type = "purgekick"

        db.session.add(log)
        db.session.commit()

        await ctx.guild.ban(user=user, reason=reason, delete_message_days=daystodelete)
        await ctx.guild.unban(user, reason=reason)
        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(KickCog(bot))
