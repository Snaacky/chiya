import logging
import time

import discord
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from utils import database, embeds
from utils.config import config
from utils.moderation import can_action_member


log = logging.getLogger(__name__)


class BanCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    async def is_user_banned(self, ctx: SlashContext, user: discord.User) -> bool:
        """
        Checks if the user if the user is banned.

        Args:
            ctx (SlashContext): The context of the slash command.
            user (discord.User): The user to be checked.

        Returns:
            True if the user is banned, False otherwise.

        Raises:
            discord.NotFound: Raised if the user is not found in the ban list.
        """
        try:
            return await self.bot.get_guild(ctx.guild.id).fetch_ban(user)
        except discord.NotFound:
            return False

    @cog_ext.cog_slash(
        name="ban",
        description="Bans the user from the server",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="user",
                description="The member that will be banned",
                option_type=6,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the member is being banned",
                option_type=3,
                required=True
            ),
            create_option(
                name="daystodelete",
                description="The number of days of messages to delete from the member, up to 7",
                option_type=4,
                required=False
            ),
        ],
        default_permission=False,
        permissions={
            config["guild_id"]: [
                create_permission(config["roles"]["staff"], SlashCommandPermissionType.ROLE, True),
                create_permission(config["roles"]["trial_mod"], SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def ban(self, ctx: SlashContext, user: discord.User, reason: str, daystodelete: int = 0):
        """
        Slash command for banning users from the server.

        Args:
            ctx (SlashContext): The context of the slash command.
            user (discord.User): The user to ban from the server.
            reason (str): The reason provided by the staff member issuing the ban.
            daystodelete (int): The days of messages to delete from the banned user.

        Notes:
            delete_message_days is capped at 7 days maximum, this is a Discord API limitation.

        Raises:
            discord.errors.Forbidden: Raised when unable to message the banned user due to
            them having privacy settings enabled, not being in the server, or having the bot
            blocked.
        """
        await ctx.defer()

        if isinstance(user, discord.Member):
            if not await can_action_member(ctx=ctx, member=user):
                return await embeds.error_message(ctx=ctx, description=f"You cannot action {user.mention}.")
        else:
            user = await self.bot.fetch_user(user)

        if await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.error_message(ctx=ctx, description=f"{user.mention} is already banned.")

        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Banning user: {user}",
            description=f"{user.mention} was banned by {ctx.author.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/l0jyxkz.png",
            color="soft_red"
        )

        try:
            channel = await user.create_dm()
            dm_embed = embeds.make_embed(
                author=False,
                title="Uh-oh, you've been banned!",
                description=(
                    "You can submit a ban appeal on our subreddit [here]"
                    "(https://www.reddit.com/message/compose/?to=/r/animepiracy)."
                ),
                color=0xc2bac0
            )
            dm_embed.add_field(name="Server:", value=f"[{ctx.guild}](https://discord.gg/piracy)", inline=True)
            dm_embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            dm_embed.add_field(name="Length:", value="Indefinite", inline=True)
            dm_embed.add_field(name="Reason:", value=reason, inline=False)
            dm_embed.set_image(url="https://i.imgur.com/CglQwK5.gif")
            await channel.send(embed=dm_embed)
        except discord.errors.Forbidden:
            embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {user.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                )
            )

        await ctx.guild.ban(user=user, reason=reason, delete_message_days=daystodelete)

        db = database.Database().get()
        db["mod_logs"].insert(dict(
            user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="ban"
        ))
        db.commit()
        db.close()

        await ctx.send(embed=embed)

    @cog_ext.cog_slash(
        name="unban",
        description="Unbans the user from the server",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="user",
                description="The user that will be unbanned",
                option_type=6,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the user is being unbanned",
                option_type=3,
                required=True
            ),
        ],
        default_permission=False,
        permissions={
            config["guild_id"]: [
                create_permission(config["roles"]["staff"], SlashCommandPermissionType.ROLE, True),
                create_permission(config["roles"]["trial_mod"], SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def unban(self, ctx: SlashContext, user: discord.User, reason: str):
        """
        Slash command for unbanning users from the server.

        Args:
            ctx (SlashContext): The context of the slash command.
            user (discord.User): The user to unban from the server.
            reason (str): The reason provided by the staff member issuing the unban.
        """
        await ctx.defer()

        if not isinstance(user, discord.User):
            user = await self.bot.fetch_user(user)

        if not await self.is_user_banned(ctx=ctx, user=user):
            return await embeds.error_message(ctx=ctx, description=f"{user.mention} is not banned.")

        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Unbanning user: {user}",
            description=f"{user.mention} was unbanned by {ctx.author.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/4H0IYJH.png",
            color="soft_green"
        )

        embed.add_field(
            name="Notice:",
            value=(
                f"Unable to message {user.mention} about this action "
                "because they are not in the server."
            )
        )

        try:
            await ctx.guild.unban(user=user, reason=reason)
        except discord.HTTPException:
            return

        db = database.Database().get()
        db["mod_logs"].insert(dict(
            user_id=user.id,
            mod_id=ctx.author.id,
            timestamp=int(time.time()),
            reason=reason,
            type="unban"
        ))
        db.commit()
        db.close()

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(BanCog(bot))
    log.info("Commands loaded: bans")
