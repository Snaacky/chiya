import arrow

import discord
from discord import app_commands
from discord.ext import commands

from chiya.config import config
from chiya.database import ModLog
from chiya.utils import embeds
from chiya.utils.helpers import log_embed_to_channel


class WarnCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="warn", description="Warn the member")
    @app_commands.guilds(config.guild_id)
    @app_commands.guild_only()
    @app_commands.describe(member="The member that will be warned")
    @app_commands.describe(reason="The reason why the member is being warned")
    async def warn(self, ctx: discord.Interaction, member: discord.Member | discord.User, reason: str) -> None:
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

        if not isinstance(member, discord.Member):
            return await embeds.send_error(ctx=ctx, description="That user is not in the server.")

        if len(reason) > 4096:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 4096 characters.")

        mod_embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title="Warned member",
            description=f"{member.mention} was warned by {ctx.user.mention}",
            thumbnail_url="https://files.catbox.moe/xbwoe8.png",
            color=discord.Color.gold(),
            fields=[
                {"name": "Reason:", "value": reason, "inline": False},
            ],
        )

        try:
            user_embed = embeds.make_embed(
                author=False,
                title="Uh-oh, you've received a warning!",
                description="If you believe this was a mistake, contact staff.",
                image_url="https://files.catbox.moe/2mscuu.gif",
                color=discord.Color.blurple(),
                fields=[
                    {"name": "Server:", "value": ctx.guild.name, "inline": True},
                    {"name": "Reason:", "value": reason, "inline": False},
                ],
            )
            await member.send(embed=user_embed)
        except (discord.Forbidden, discord.HTTPException):
            mod_embed.set_footer(text="⚠️ Unable to message user about this action.")

        ModLog(
            user_id=member.id,
            mod_id=ctx.user.id,
            timestamp=arrow.utcnow().int_timestamp,
            reason=reason,
            type="warn",
        ).save()

        await ctx.followup.send(embed=mod_embed)
        await log_embed_to_channel(ctx=ctx, embed=mod_embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WarnCog(bot))
