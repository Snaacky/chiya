import logging
import time

import discord
from discord.commands import Option, context, slash_command
from discord.ext import commands

from chiya import config, database
from chiya.utils import embeds


log = logging.getLogger(__name__)


class WarnCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @slash_command(guild_ids=config["guild_ids"], description="Warn the member")
    @commands.has_role(config["roles"]["staff"])
    async def warn(
        self,
        ctx: context.ApplicationContext,
        member: Option(discord.Member | discord.User, description="The member that will be warned", required=True),
        reason: Option(str, description="The reason why the member is being warned", required=True),
    ) -> None:
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
        await ctx.defer()

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if len(reason) > 4096:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 4096 characters.")

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title=f"Warning member: {member.name}",
            description=f"{member.mention} was warned by {ctx.author.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/4jeFA3h.png",
            color=discord.Color.gold(),
        )

        try:
            dm_embed = embeds.make_embed(
                author=False,
                title="Uh-oh, you've received a warning!",
                description="If you believe this was a mistake, contact staff.",
                image_url="https://i.imgur.com/rVf0mlG.gif",
                color=discord.Color.blurple(),
                fields=[
                    {
                        "name": "Server:",
                        "value": f"[{ctx.guild.name}]({await ctx.guild.vanity_invite()})",
                        "inline": True,
                    },
                    {"name": "Moderator:", "value": ctx.author.mention, "inline": True},
                    {"name": "Reason:", "value": reason, "inline": False},
                ],
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            embed.add_field(
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
                type="warn",
            )
        )

        db.commit()
        db.close()

        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(WarnCommands(bot))
    log.info("Commands loaded: warn")
