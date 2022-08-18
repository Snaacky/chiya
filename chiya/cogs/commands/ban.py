import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

from chiya import config, database
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member


log = logging.getLogger(__name__)


class BansCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def is_user_banned(self, ctx: discord.Interaction, user: discord.Member | discord.User) -> bool:
        """
        Check if the user is banned from the context invoking guild.
        """
        try:
            return bool(await self.bot.get_guild(ctx.guild.id).fetch_ban(user))
        except discord.NotFound:
            return False

    @app_commands.command(name="ban", description="Ban user from the server")
    @app_commands.guilds(config["guild_id"])
    @app_commands.describe(user="User to ban from the server")
    @app_commands.describe(reason="Reason why the user is being banned")
    @app_commands.describe(daystodelete="Days worth of messages to delete from the user, up to 7")
    @app_commands.checks.has_role(config["roles"]["staff"])
    @app_commands.guild_only()
    async def ban(
        self,
        ctx: discord.Interaction,
        user: discord.Member | discord.User,
        reason: str,
        daystodelete: app_commands.Range[int, 1, 7] = None
    ) -> None:
        """
        Ban the user, log the action to the database, and attempt to send them
        a direct message alerting them of their ban.

        If the user isn't in the server, has privacy settings enabled, or has
        the bot blocked they will be unable to receive the ban notification.
        The bot will let the invoking mod know if this is the case.

        daystodelete is limited to a maximum value of 7. This is a Discord API
        limitation with the .ban() function.
        """
        await ctx.response.defer(thinking=True)

        if not await can_action_member(ctx=ctx, member=user):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {user.mention}.")

        if await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.error_message(ctx=ctx, description=f"{user.mention} is already banned.")

        if len(reason) > 1024:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 1024 characters.")

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title=f"Banning user: {user}",
            description=f"{user.mention} was banned by {ctx.user.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/l0jyxkz.png",
            color=discord.Color.red(),
        )

        dm_embed = embeds.make_embed(
            author=False,
            title="Uh-oh, you've been banned!",
            description=(
                "You can submit a ban appeal on our subreddit [here]"
                "(https://www.reddit.com/message/compose/?to=/r/snackbox)."
            ),
            image_url="https://i.imgur.com/CglQwK5.gif",
            color=discord.Color.blurple(),
            fields=[
                {"name": "Server:", "value": f"[{ctx.guild.name}]({await ctx.guild.vanity_invite()})", "inline": True},
                {"name": "Moderator:", "value": ctx.user.mention, "inline": True},
                {"name": "Reason:", "value": reason, "inline": True},
            ],
        )

        try:
            await user.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {user.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                ),
            )

        db = database.Database().get()
        db["mod_logs"].insert(
            dict(
                user_id=user.id,
                mod_id=ctx.user.id,
                timestamp=int(time.time()),
                reason=reason,
                type="ban",
            )
        )
        db.commit()
        db.close()

        await ctx.guild.ban(user=user, reason=reason, delete_message_days=daystodelete or 0)
        await ctx.followup.send(embed=embed)

    @app_commands.command(name="unban", description="Unban user from the server")
    @app_commands.guilds(config["guild_id"])
    @app_commands.describe(user="User to unban from the server")
    @app_commands.describe(reason="Reason why the user is being unbanned")
    @app_commands.checks.has_role(config["roles"]["staff"])
    @app_commands.guild_only()
    async def unban(self, ctx: discord.Interaction, user: discord.Member | discord.User, reason: str) -> None:
        """
        Unban the user from the server and log the action to the database.

        Unlike when the user is banned, the bot is completely unable to let
        the user know that they were unbanned because it cannot communicate
        with users that it does not share a mutual server with.
        """
        await ctx.response.defer(thinking=True)

        if not await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.error_message(ctx=ctx, description=f"{user.mention} is not banned.")

        if len(reason) > 1024:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 1024 characters.")

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title=f"Unbanning user: {user}",
            description=f"{user.mention} was unbanned by {ctx.user.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/4H0IYJH.png",
            color=discord.Color.green(),
        )

        db = database.Database().get()
        db["mod_logs"].insert(
            dict(user_id=user.id, mod_id=ctx.user.id, timestamp=int(time.time()), reason=reason, type="unban")
        )
        db.commit()
        db.close()

        await ctx.guild.unban(user=user, reason=reason)
        await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BansCommands(bot))
    log.info("Commands loaded: ban")
