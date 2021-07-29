import datetime
import logging
import re
import time

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

import config
from utils import database
from utils import embeds
from utils.moderation import can_action_member
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class RestrictCog(Cog):
    """ Restrict Cog """

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def is_user_restricted(ctx: SlashContext, member: discord.Member) -> bool:
        if discord.utils.get(ctx.guild.roles, id=config.role_restricted) in member.roles:
            return True
        return False

    @staticmethod
    async def restrict_member(ctx: SlashContext, member: discord.Member, reason: str, temporary: bool = False, end_time: float = None) -> None:
        role = discord.utils.get(ctx.guild.roles, id=config.role_restricted)
        await member.add_roles(role, reason=reason)

        # Add the restrict to the mod_log database.
        with dataset.connect(database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="restrict"
            ))

            # Occurs when the duration in /restrict is specified (temporary restrict).
            if temporary:
                db["timed_mod_actions"].insert(dict(
                    user_id=member.id,
                    mod_id=ctx.author.id,
                    action_type="restrict",
                    reason=reason,
                    start_time=datetime.datetime.now(tz=datetime.timezone.utc).timestamp(),
                    end_time=end_time,
                    is_done=False
                ))

    async def unrestrict_member(self, member: discord.Member, reason: str, ctx: SlashContext = None, guild: discord.Guild = None) -> None:
        guild = guild or ctx.guild
        moderator = ctx.author if ctx else self.bot.user

        # Removes "Restricted" role from member.
        role = discord.utils.get(guild.roles, id=config.role_restricted)
        await member.remove_roles(role, reason=reason)

        # Add the unrestrict to the mod_log database.
        with dataset.connect(database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=moderator.id, timestamp=int(time.time()), reason=reason, type="unrestrict"
            ))

    @staticmethod
    async def send_restricted_dm_embed(ctx: SlashContext, member: discord.Member, reason: str = None, duration: str = None) -> bool:
        if not duration:
            duration = "Indefinite"

        try:  # In case user has DMs blocked.
            dm_channel = await member.create_dm()
            embed = embeds.make_embed(
                author=False,
                title=f"Uh-oh, you've been restricted!",
                description="If you believe this was a mistake, contact staff.",
                color=0x8083b0
            )
            embed.add_field(name="Server:", value=f"[{ctx.guild}](https://discord.gg/piracy/)", inline=True)
            embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            embed.add_field(name="Length:", value=duration, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/KE1jNl3.gif")
            await dm_channel.send(embed=embed)
            return True
        except discord.HTTPException:
            return False

    async def send_unrestricted_dm_embed(self, member: discord.Member, reason: str, ctx: SlashContext = None, guild: discord.Guild = None) -> bool:
        guild = guild or ctx.guild
        moderator = ctx.author if ctx else self.bot.user

        # Send member message telling them that they were unrestricted and why.
        try:  # In case user has DMs blocked.
            channel = await member.create_dm()
            embed = embeds.make_embed(
                author=False,
                title=f"Yay, you've been unrestricted!",
                description="Review our server rules to avoid being actioned again in the future.",
                color=0x8a3ac5
            )
            embed.add_field(name="Server:", value=f"[{guild}](https://discord.gg/piracy/)", inline=True)
            embed.add_field(name="Moderator:", value=moderator.mention, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/U5Fvr2Y.gif")
            await channel.send(embed=embed)
            return True
        except discord.HTTPException:
            return False

    @commands.bot_has_permissions(manage_roles=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="restrict",
        description="Restricts message permissions from the member for the specified length of time",
        guild_ids=[config.guild_id],
        options=[
            create_option(
                name="member",
                description="The member that will be restricted",
                option_type=6,
                required=True
            ),
            create_option(
                name="duration",
                description="The length of time the user will be restricted for",
                option_type=3,
                required=False
            ),
            create_option(
                name="reason",
                description="The reason why the member is being restricted",
                option_type=3,
                required=False
            ),
        ],
        default_permission=False,
        permissions={
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
                create_permission(config.role_trial_mod, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def restrict(self, ctx: SlashContext, member: discord.Member, duration: str = None, reason: str = None):
        """ Temporarily restrict member in guild. """
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(member, int):
            await embeds.error_message(ctx=ctx, description=f"That user is not in the server.")
            return

        # Checks if invoker can action that member (self, bot, etc.)
        if not await can_action_member(bot=self.bot, ctx=ctx, member=member):
            await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")
            return

        # Check if the user is restricted already.
        if await self.is_user_restricted(ctx=ctx, member=member):
            await embeds.error_message(ctx=ctx, description=f"{member.mention} is already restricted.")
            return

        # Automatically default the reason string to N/A when the moderator does not provide a reason.
        if not reason:
            reason = "No reason provided."
        # Discord caps embed fields at a ridiculously low character limit, avoids problems with future embeds.
        elif len(reason) > 512:
            await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")
            return

        # If duration is not specified, default it to a permanent restrict.
        if not duration:
            # Start creating the embed that will be used to alert the moderator that the user was successfully restricted.
            embed = embeds.make_embed(
                ctx=ctx,
                title=f"Restricting member: {member.name}",
                description=f"{member.mention} was restricted by {ctx.author.mention} for: {reason}",
                thumbnail_url=config.user_restrict,
                color="soft_red"
            )

            # Attempt to DM the user to let them know they were restricted.
            if not await self.send_restricted_dm_embed(ctx=ctx, member=member, reason=reason):
                embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. This can be caused by the user not being in the server, having DMs disabled, or having the bot blocked.")

            # Restricts the user and returns the embed letting the moderator know they were successfully restricted.
            await self.restrict_member(ctx=ctx, member=member, reason=reason)
            await ctx.send(embed=embed)
            return

        # RegEx stolen from Setsudo and modified.
        regex = r"((?:(\d+)\s*d(?:ays)?)?\s*(?:(\d+)\s*h(?:ours|rs|r)?)?\s*(?:(\d+)\s*m(?:inutes|in)?)?\s*(?:(\d+)\s*s(?:econds|ec)?)?)"

        # Get all of the matches from the RegEx.
        try:
            match_list = re.findall(regex, duration)[0]
        except discord.HTTPException:
            await embeds.error_message(ctx=ctx, description="Duration syntax: `#d#h#m#s` (day, hour, min, sec)\nYou can specify up to all four but you only need one.")
            return

        # Check if all the matches are blank and return preemptively if so.
        if not any(x.isalnum() for x in match_list):
            await embeds.error_message(ctx=ctx, description="Duration syntax: `#d#h#m#s` (day, hour, min, sec)\nYou can specify up to all four but you only need one.")
            return

        duration = dict(
            days=match_list[1],
            hours=match_list[2],
            minutes=match_list[3],
            seconds=match_list[4]
        )

        # String that will store the duration in a more digestible format.
        duration_string = ""
        for time_unit in duration:
            # If the time value is undeclared, set it to 0 and skip it.
            if duration[time_unit] == "":
                duration[time_unit] = 0
                continue
            # If the time value is 1, make the time unit into singular form.
            if duration[time_unit] == "1":
                duration_string += f"{duration[time_unit]} {time_unit[:-1]} "
            else:
                duration_string += f"{duration[time_unit]} {time_unit} "
            # Updating the values for ease of conversion to timedelta object later.
            duration[time_unit] = float(duration[time_unit])

        restrict_end_time = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
            days=duration["days"],
            hours=duration["hours"],
            minutes=duration["minutes"],
            seconds=duration["seconds"]
        )

        # Start creating the embed that will be used to alert the moderator that the user was successfully restricted.
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Restricting member: {member}",
            description=f"{member.mention} was restricted by {ctx.author.mention} for: {reason}",
            thumbnail_url=config.user_restrict,
            color="soft_red"
        )
        embed.add_field(name="Duration:", value=duration_string, inline=False)

        # Attempt to DM the user to let them know they were restricted.
        if not await self.send_restricted_dm_embed(ctx=ctx, member=member, reason=reason, duration=duration_string):
            embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. This can be caused by the user not being in the server, having DMs disabled, or having the bot blocked.")

        # Restricts the user and stores the unrestrict time in the database for the background task.
        await self.restrict_member(ctx=ctx, member=member, reason=reason, temporary=True, end_time=restrict_end_time.timestamp())
        await ctx.send(embed=embed)

    @commands.bot_has_permissions(manage_roles=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="unrestrict",
        description="Unrestricts the member",
        guild_ids=[config.guild_id],
        options=[
            create_option(
                name="member",
                description="The member that will be unrestricted",
                option_type=6,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the member is being unrestricted",
                option_type=3,
                required=False
            ),
        ],
        default_permission=False,
        permissions={
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
                create_permission(config.role_trial_mod, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def unrestrict(self, ctx: SlashContext, member: discord.Member, reason: str = None):
        """ Unrestricts member in guild. """
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(member, int):
            await embeds.error_message(ctx=ctx, description=f"That user is not in the server.")
            return

        # Checks if invoker can action that member (self, bot, etc.)
        if not await can_action_member(bot=self.bot, ctx=ctx, member=member):
            await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")
            return

        # Check if the user is not restricted already.
        if not await self.is_user_restricted(ctx=ctx, member=member):
            await embeds.error_message(ctx=ctx, description=f"{member.mention} is not restrictd.")
            return

        # Automatically default the reason string to N/A when the moderator does not provide a reason.
        if not reason:
            reason = "No reason provided."
        # Discord caps embed fields at a ridiculously low character limit, avoids problems with future embeds.
        elif len(reason) > 512:
            await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")
            return

        # Start creating the embed that will be used to alert the moderator that the user was successfully unrestricted.
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Unrestricting member: {member.name}",
            description=f"{member.mention} was unrestrictd by {ctx.author.mention} for: {reason}",
            color="soft_green",
            thumbnail_url=config.user_unrestrict
        )

        # Unrestricts the user.
        await self.unrestrict_member(ctx=ctx, member=member, reason=reason)

        # Attempt to DM the user to let them and the mods know they were unrestricted.
        if not await self.send_unrestricted_dm_embed(ctx=ctx, member=member, reason=reason):
            embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. This can be caused by the user not being in the server, having DMs disabled, or having the bot blocked.")

        # If the mod sent the /unrestrict in the restrict channel, this will cause a errors.NotFound 404.
        # We cannot send the embed and then archive the channel because that will cause a error.AlreadyResponded.
        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            pass


def setup(bot: Bot) -> None:
    """ Load the restrict cog. """
    bot.add_cog(RestrictCog(bot))
    log.info("Commands loaded: restricts")
