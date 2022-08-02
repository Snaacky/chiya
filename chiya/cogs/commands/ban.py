import logging
import time

import discord
from discord.commands import Option, context, slash_command
from discord.ext import commands

from chiya import config, database
from chiya.utils import embeds
from chiya.utils.helpers import can_action_member


log = logging.getLogger(__name__)


class BansCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def is_user_banned(self, ctx: context.ApplicationContext, user: discord.Member | discord.User) -> bool:
        """
        Check if the user is banned from the context invoking guild.
        """
        try:
            return bool(await self.bot.get_guild(ctx.guild.id).fetch_ban(user))
        except discord.NotFound:
            return False

    @slash_command(guild_ids=config["guild_ids"])
    @commands.has_role(config["roles"]["staff"])
    async def ban(
        self,
        ctx: context.ApplicationContext,
        user: Option(discord.Member | discord.User, description="User to ban from the server", required=True),
        reason: Option(str, description="Reason why the user is being banned", required=True),
        daystodelete: Option(
            int,
            description="Days worth of messages to delete from the user, up to 7",
            choices=[1, 2, 3, 4, 5, 6, 7],
            required=False,
        ),
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
        await ctx.defer()

        if isinstance(user, discord.Member):
            if not await can_action_member(ctx=ctx, member=user):
                return await embeds.error_message(ctx=ctx, description=f"You cannot action {user.mention}.")
        else:  # TODO: is this really the best way to handle this?
            user = await self.bot.fetch_user(user)

        if await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.error_message(ctx=ctx, description=f"{user.mention} is already banned.")

        if len(reason) > 1024:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 1024 characters.")

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title=f"Banning user: {user}",
            description=f"{user.mention} was banned by {ctx.author.mention} for: {reason}",
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
                {"name": "Moderator:", "value": ctx.author.mention, "inline": True},
                {"name": "Reason:", "value": reason, "inline": True},
            ],
        )

        try:
            await user.send(embed=dm_embed)
        except discord.Forbidden:
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
                mod_id=ctx.author.id,
                timestamp=int(time.time()),
                reason=reason,
                type="ban",
            )
        )
        db.commit()
        db.close()

        await ctx.guild.ban(user=user, reason=reason, delete_message_days=daystodelete or 0)
        await ctx.send_followup(embed=embed)

    @slash_command(guild_ids=config["guild_ids"])
    @commands.has_role(config["roles"]["staff"])
    async def unban(
        self,
        ctx: context.ApplicationContext,
        user: Option(discord.Member | discord.User, description="User to unban from the server", required=True),
        reason: Option(str, description="Reason why the user is being unbanned", required=True),
    ) -> None:
        """
        Unban the user from the server and log the action to the database.

        Unlike when the user is banned, the bot is completely unable to let
        the user know that they were unbanned because it cannot communicate
        with users that it does not share a mutual server with.
        """
        await ctx.defer()

        if not isinstance(user, discord.User):
            user = await self.bot.fetch_user(user)

        if not await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.error_message(ctx=ctx, description=f"{user.mention} is not banned.")

        if len(reason) > 1024:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 1024 characters.")

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title=f"Unbanning user: {user}",
            description=f"{user.mention} was unbanned by {ctx.author.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/4H0IYJH.png",
            color=discord.Color.green(),
        )

        db = database.Database().get()
        db["mod_logs"].insert(
            dict(user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="unban")
        )
        db.commit()
        db.close()

        await ctx.guild.unban(user=user, reason=reason)
        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(BansCommands(bot))
    log.info("Commands loaded: ban")
