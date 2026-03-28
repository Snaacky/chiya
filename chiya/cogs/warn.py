import discord
from discord import app_commands
from discord.ext import commands

from chiya import db
from chiya.config import config
from chiya.models import ModLog
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member, log_embed_to_channel


class WarnCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="warn", description="Warn the member")
    @app_commands.guilds(config.guild_id)
    @app_commands.describe(user="The member that will be warned")
    @app_commands.describe(reason="The reason why the member is being warned")
    async def warn(self, ctx: discord.Interaction, user: discord.User | discord.Member, reason: str) -> None:
        """
        Warn the user, log the action to the database, and attempt to send
        them a direct message alerting them of their mute.

        The warning does not inherently apply any sort of punishment and is
        merely used for keeping track of rule breaking offenses to be used
        when considering future mod actions.

        If the user isn't in the server, has privacy settings enabled, or has
        the bot blocked they will be unable to receive the ban notification.
        The bot will let the invoking mod know if this is the case.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not ctx.guild:
            return

        if not isinstance(user, discord.Member):
            return await embeds.send_error(ctx=ctx, description="That user is not in the server.")

        if not can_action_member(ctx=ctx, member=user):
            return await embeds.send_error(ctx=ctx, description=f"You cannot action {user.mention}.")

        if len(reason) > 4096:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 4096 characters.")

        mod_embed = discord.Embed()
        mod_embed.title = "Warned member"
        mod_embed.description = f"{user.mention} was warned by {ctx.user.mention}"
        mod_embed.color = discord.Color.gold()
        mod_embed.add_field(name="Reason:", value=reason, inline=False)
        mod_embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)
        mod_embed.set_thumbnail(url="https://files.catbox.moe/xbwoe8.png")

        user_embed = discord.Embed()
        user_embed.title = "Uh-oh, you've received a warning!"
        user_embed.description = "If you believe this was a mistake, contact staff."
        user_embed.color = discord.Color.blurple()
        user_embed.add_field(name="Server:", value=ctx.guild.name, inline=True)
        user_embed.add_field(name="Reason:", value=reason, inline=False)
        user_embed.set_image(url="https://files.catbox.moe/2mscuu.gif")

        try:
            await user.send(embed=user_embed)
        except discord.Forbidden, discord.HTTPException:
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        log = ModLog()
        log.user_id = user.id
        log.mod_id = ctx.user.id
        log.timestamp = int(ctx.created_at.timestamp())
        log.reason = reason
        log.type = "warn"

        db.session.add(log)
        db.session.commit()

        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WarnCog(bot))
