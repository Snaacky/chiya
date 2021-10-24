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


class KickCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="kick",
        description="Kicks the member from the server",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="member",
                description="The member that will be kicked",
                option_type=6,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the member is being kicked",
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
    async def kick_member(self, ctx: SlashContext, member: discord.Member, reason: str):
        """
        Slash command for kicking users from the server.

        Args:
            ctx (SlashContext): The context of the slash command.
            member (discord.Member): The user to ban from the server.
            reason (str): The reason provided by the staff member issuing the ban.

        Raises:
            discord.errors.Forbidden: Unable to message the user due to privacy settings,
            not being in the server, or having the bot blocked.
        """
        await ctx.defer()

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Kicking member: {member.name}",
            description=f"{member.mention} was kicked by {ctx.author.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/l0jyxkz.png",
            color="soft_red"
        )

        try:
            channel = await member.create_dm()
            dm_embed = embeds.make_embed(
                title="Uh-oh, you've been kicked!",
                description="I-I guess you can join back if you want? B-baka!",
                image_url="https://i.imgur.com/UkrBRur.gif",
                author=False,
                color=0xe49bb3
            )
            dm_embed.add_field(name="Server:", value=f"[{ctx.guild}](https://discord.gg/piracy)", inline=True)
            dm_embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            dm_embed.add_field(name="Reason:", value=reason, inline=False)
            await channel.send(embed=dm_embed)
        except discord.errors.Forbidden:
            embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                )
            )

        await ctx.guild.kick(user=member, reason=reason)

        db = database.Database().get()
        db["mod_logs"].insert(dict(
            user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="kick"
        ))
        db.commit()
        db.close()
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(KickCog(bot))
    log.info("Commands loaded: kicks")
