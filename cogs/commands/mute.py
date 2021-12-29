import datetime
import logging
import time

import discord
from discord.commands import Option, context, permissions, slash_command
from discord.ext import commands

import utils.duration
from utils import database, embeds
from utils.config import config
from utils.moderation import can_action_member

log = logging.getLogger(__name__)


class MuteCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_ids=config["guild_ids"], default_permission=False, description="Mutes a member in the server")
    @permissions.has_role(config["roles"]["staff"])
    async def mute(
        self,
        ctx: context.ApplicationContext,
        member: Option(discord.Member, description="The member that will be kicked", required=True),
        reason: Option(str, description="The reason why the member is being kicked", required=True),
        duration: Option(str, description="The length of time the user will be muted for", required=True)
    ) -> bool:
        """
        Mute the user from the server. Attempt to alert them of their mute via direct message.

        Args:
            ctx (context.ApplicationContext): Context for the function invoke.
            member (discord.Member): Member to mute from the server.
            reason (str): Reason why the user is being muted.
            duration (int): Length of time the user will be muted for.

        Returns:
            True (bool): User was successfully muted from the server.
            False (bool): User is not in the server.
            False (bool): Invoking mod cannot action the user specified due to permissions.
            False (bool): User is already muted from the server.
            False (bool): Reason parameter was more than 512 characters.
            False (bool): Incorrect syntax for duration parameter.
        """
        await ctx.defer()

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        if member.timed_out:
            return await embeds.error_message(ctx=ctx, description=f"{member.mention} is already muted.")

        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        duration_string, mute_end_time = utils.duration.get_duration(duration=duration)
        if not duration_string:
            return await embeds.error_message(
                ctx=ctx,
                description=(
                    "Duration syntax: `#d#h#m#s` (day, hour, min, sec)\n"
                    "You can specify up to all four but you only need one."
                ))

        mute_embed = embeds.make_embed(
            ctx=ctx,
            title=f"Muting member: {member}",
            description=f"{member.mention} was muted by {ctx.author.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/rHtYWIt.png",
            color="soft_red"
        )
        mute_embed.add_field(name="Duration:", value=duration_string, inline=False)
        
        try:
            dm_embed = embeds.make_embed(
                author=False,
                title="Uh-oh, you've been muted!",
                description="If you believe this was a mistake, contact staff.",
                image_url="https://i.imgur.com/840Q48l.gif",
                color=0x8083B0,
            )
            dm_embed.add_field(name="Server:", value=f"[{ctx.guild}](https://discord.gg/piracy)", inline=True)
            dm_embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            dm_embed.add_field(name="Length:", value=duration, inline=True)
            dm_embed.add_field(name="Reason:", value=reason, inline=False)
            dm_channel = await member.create_dm()
            await dm_channel.send(embed=dm_embed)
        except discord.HTTPException:
            mute_embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                ))

        db = database.Database().get()
        db["mod_logs"].insert(
            dict(
                user_id=member.id,
                mod_id=ctx.author.id,
                timestamp=int(time.time()),
                reason=reason,
                type="mute",
            )
        )
        db.commit()
        db.close()

        # TODO: what happens if the user doesn't have permission for timeouts?
        await member.timeout(until=datetime.datetime.utcfromtimestamp(mute_end_time), reason=reason)
        await ctx.send_followup(embed=mute_embed)
        return True

    @slash_command(guild_ids=config["guild_ids"], default_permission=False, description="Unmute a member in the server")
    @permissions.has_role(config["roles"]["staff"])
    async def unmute(
        self,
        ctx: context.ApplicationContext,
        member: Option(discord.Member, description="The member that will be unmuted", required=True),
        reason: Option(str, description="The reason why the member is being kicked", required=True),
    ):
        """
        Unmute the user from the server. Attempt to alert them of their mute via direct message.

        Args:
            ctx (context.ApplicationContext): Context for the function invoke.
            member (discord.Member): Member to mute from the server.
            reason (str): Reason why the user is being muted.

        Returns:
            True (bool): User was successfully unmuted from the server.
            False (bool): User is not in the server.
            False (bool): Invoking mod cannot action the user specified due to permissions.
            False (bool): User is not muted from the server.
            False (bool): Reason parameter was more than 512 characters.
        """
        await ctx.defer()

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        if not member.timed_out:
            return await embeds.error_message(ctx=ctx, description=f"{member.mention} is not muted.")

        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        unmute_embed = embeds.make_embed(
            ctx=ctx,
            title=f"Unmuting member: {member.name}",
            description=f"{member.mention} was unmuted by {ctx.author.mention} for: {reason}",
            color="soft_green",
            thumbnail_url="https://i.imgur.com/W7DpUHC.png",
        )

        try:
            dm_embed = embeds.make_embed(
                author=False,
                title="Yay, you've been unmuted!",
                description="Review our server rules to avoid being actioned again in the future.",
                image_url="https://i.imgur.com/U5Fvr2Y.gif",
                color=0x8A3AC5,
            )
            dm_embed.add_field(name="Server:", value="[/r/animepiracy](https://discord.gg/piracy)", inline=True)
            dm_embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            dm_embed.add_field(name="Reason:", value=reason, inline=False)
            channel = await member.create_dm()
            await channel.send(embed=dm_embed)
        except discord.HTTPException:
            unmute_embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                ))

        db = database.Database().get()
        db["mod_logs"].insert(
            dict(
                user_id=member.id,
                mod_id=ctx.author.id,
                timestamp=int(time.time()),
                reason=reason,
                type="unmute",
            ))

        db.commit()
        db.close()

        await member.remove_timeout(reason=reason)
        await ctx.send_followup(embed=unmute_embed)


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(MuteCommands(bot))
    log.info("Commands loaded: mute")
