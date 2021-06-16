import datetime
import logging
import re
import time

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_permission
from discord_slash.model import SlashCommandPermissionType

import config
from utils import database
from utils import embeds
from utils.record import record_usage
from utils.moderation import can_action_member

# Enabling logs
log = logging.getLogger(__name__)


class BanCog(Cog):
    """ Ban Cog """

    def __init__(self, bot):
        self.bot = bot

    async def ban_member(self, ctx: SlashContext, user: discord.User, reason: str, temporary: bool = False, end_time: float = None) -> None:
        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.ban
        await ctx.guild.ban(user=user, reason=reason, delete_message_days=0)

        # Add the ban to the mod_log database.
        with dataset.connect(database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="ban"
            ))

            # Stores the action in a separate table for the scheduler to handle unbanning later.
            if temporary:
                db["timed_mod_actions"].insert(dict(
                    user_id=user.id,
                    mod_id=ctx.author.id,
                    action_type="ban",
                    reason=reason,
                    start_time=datetime.datetime.now(tz=datetime.timezone.utc).timestamp(),
                    end_time=end_time,
                    is_done=False
                ))

    async def unban_user(self, user: discord.User, reason: str, ctx: SlashContext = None, guild: discord.Guild = None) -> None:
        guild = guild or ctx.guild
        moderator = ctx.author if ctx else self.bot.user

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.unban
        try:
            await guild.unban(user=user, reason=reason)
        except discord.HTTPException:
            return

        # Add the unban to the mod_log database.
        with dataset.connect(database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=moderator.id, timestamp=int(time.time()), reason=reason, type="unban"
            ))

    async def is_user_in_guild(self, guild: discord.Guild, user: discord.User) -> bool:
        guild = self.bot.get_guild(guild)
        member = guild.get_member(user.id)
        if member:
            return member
        return False

    async def is_user_banned(self, guild: discord.Guild, user: discord.User) -> bool:
        # Checks to see if the user is already banned.
        guild = self.bot.get_guild(guild)
        try:
            await guild.fetch_ban(user)
            return True
        except discord.HTTPException:
            return False

    async def send_banned_dm_embed(self, ctx: SlashContext, user: discord.User, reason: str = None, duration: str = None) -> bool:
        if not duration:
            duration = "Indefinite"

        try:  # In case user has DM Blocked.
            channel = await user.create_dm()
            embed = embeds.make_embed(author=False, color=0xc2bac0)
            embed.title = f"Uh-oh, you've been banned!"
            embed.description = "You can submit a ban appeal on our subreddit [here](https://www.reddit.com/message/compose/?to=/r/animepiracy)."
            embed.add_field(name="Server:", value=ctx.guild, inline=True)
            embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            embed.add_field(name="Length:", value=duration, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/CglQwK5.gif")
            await channel.send(embed=embed)
        except discord.HTTPException:
            return False
        return True

    @commands.bot_has_permissions(ban_members=True, send_messages=True, embed_links=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="ban", 
        description="Bans the member indefinitely",
        guild_ids=[622243127435984927],
        options=[
            create_option(
                name="member",
                description="The member that will be banned",
                option_type=6,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the member is being banned",
                option_type=3,
                required=False
            ),
        ],
        default_permission=False,
        permissions={
            622243127435984927: [
                create_permission(763031634379276308, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def ban(self, ctx: SlashContext, user: discord.User, reason: str = None):
        """ Bans user from guild. """

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)
        
        # Checks if the user is already banned and let's the mod know if they already are.
        banned = await self.is_user_banned(guild=ctx.guild.id, user=user)
        if banned:
            await embeds.error_message(ctx=ctx, description=f"{user.mention} is already banned.")
            return

        # Checks to see if the mod is privileged enough to ban the user they are attempting to ban.
        member = await self.is_user_in_guild(guild=ctx.guild.id, user=user)
        if member:
            if not await can_action_member(bot=self.bot, ctx=ctx, member=member):
                await embeds.error_message(ctx=ctx, description="Could not action that member.")
                return

        # Automatically default the reason string to N/A when the moderator does not provide a reason.
        if not reason:
            reason = "No reason provided."

        # Discord caps embed fields at a ridiculously low character limit, avoids problems with future embeds.
        if reason and len(reason) > 512:
            await embeds.error_message(ctx=ctx, description=f"Reason must be less than 512 characters.")
            return

        # Start creating the embed that will be used to alert the moderator that the user was successfully banned.
        embed = embeds.make_embed(ctx=ctx, title=f"Banning user: {user.name}", thumbnail_url=config.user_ban, color="soft_red")
        embed.description = f"{user.mention} was banned by {ctx.author.mention} for: {reason}"

        # Attempt to DM the user that they have been banned with various information about their ban. 
        # If the bot was unable to DM the user, adds a notice to the output to let the mod know.
        sent = await self.send_banned_dm_embed(ctx=ctx, user=user, reason=reason)
        if not sent:
            embed.add_field(name="Notice:", value=f"Unable to message {user.mention} about this action. This can be caused by the user not being in the server, having DMs disabled, or having the bot blocked.")

        # Bans the user and returns the embed letting the moderator know they were successfully banned.
        await self.ban_member(ctx=ctx, user=user, reason=reason)
        await ctx.send(embed=embed)

    @commands.bot_has_permissions(ban_members=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="unban", 
        description="Unbans the user from the server",
        guild_ids=[622243127435984927],
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
                required=False
            ),
        ],
        default_permission=False,
        permissions={
            622243127435984927: [
                create_permission(763031634379276308, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def unban(self, ctx: SlashContext, user: discord.User, reason: str = None):
        """ Unbans user from guild. """
        user = await self.bot.fetch_user(user)

        # Checks if the user is already banned and let's the mod know if they are not.
        banned = await self.is_user_banned(guild=ctx.guild.id, user=user)
        if not banned:
            await embeds.error_message(ctx=ctx, description=f"{user.mention} is not banned.")
            return

        # Automatically default the reason string to N/A when the moderator does not provide a reason.
        if not reason:
            reason = "No reason provided."

        # Discord caps embed fields at a ridiculously low character limit, avoids problems with future embeds.
        if reason and len(reason) > 512:
            await embeds.error_message(ctx=ctx, description=f"Reason must be less than 512 characters.")
            return

        # Creates and sends the embed that will be used to alert the moderator that the user was successfully banned.
        embed = embeds.make_embed(ctx=ctx, title=f"Unbanning user: {user.name}", thumbnail_url=config.user_unban, color="soft_green")
        embed.description = f"{user.mention} was unbanned by {ctx.author.mention} for: {reason}"

        # Unbans the user and returns the embed letting the moderator know they were successfully banned.
        await self.unban_user(ctx=ctx, user=user, reason=reason)
        await ctx.send(embed=embed)

    @commands.bot_has_permissions(ban_members=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="tempban", 
        description="Bans the member for the specified length of time",
        guild_ids=[622243127435984927],
        options=[
            create_option(
                name="member",
                description="The member that will be banned",
                option_type=6,
                required=True
            ),
            create_option(
                name="duration",
                description="The length of time the user will be muted for",
                option_type=3,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the member is being banned",
                option_type=3,
                required=False
            ),
        ],
        default_permission=False,
        permissions={
            622243127435984927: [
                create_permission(763031634379276308, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def tempban(self, ctx: SlashContext, user: discord.User, duration: str, reason: str = None):
        """ Temporarily bans member from guild. """

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)
        
        # Some basic checks to make sure mods can't cause problems with their ban.
        member = await self.is_user_in_guild(guild=ctx.guild.id, user=user)
        if member:
            member = await commands.MemberConverter().convert(ctx, user.mention)
            if not await can_action_member(bot=self.bot, ctx=ctx, member=member):
                await embeds.error_message(ctx=ctx, description="Could not action that member.")
                return

        # Checks if the user is already banned and let's the mod know if they already were.
        banned = await self.is_user_banned(guild=ctx.guild.id, user=user)
        if banned:
            await embeds.error_message(ctx=ctx, description=f"{user.mention} is already banned.")
            return

        # Recycled RegEx from https://github.com/r-smashbros/setsudo/ 
        regex = r"((?:(\d+)\s*d(?:ays)?)?\s*(?:(\d+)\s*h(?:ours|rs|r)?)?\s*(?:(\d+)\s*m(?:inutes|in)?)?\s*(?:(\d+)\s*s(?:econds|ec)?)?)"

        # Attempt to parse the message argument with the Setsudo RegEx
        try:
            match_list = re.findall(regex, duration)[0]
        except:
            await embeds.error_message(ctx=ctx, description=f"Duration syntax: `#d#h#m#s` (day, hour, min, sec)\nYou can specify up to all four but you only need one.")
            return

        # Check if all the matches are blank and return preemptively if so.
        if not any(x.isalnum() for x in match_list):
            await embeds.error_message(ctx=ctx, description="Duration syntax: `#d#h#m#s` (day, hour, min, sec)\nYou can specify up to all four but you only need one.")
            return

        # Automatically default the reason string to N/A when the moderator does not provide a reason.
        if not reason:
            reason = "No reason provided."

        # Discord caps embed fields at a ridiculously low character limit, avoids problems with future embeds.
        if reason and len(reason) > 512:
            await embeds.error_message(ctx=ctx, description=f"Reason must be less than 512 characters.")
            return

        # Assign the arguments from the parsed message into variables
        duration = dict(
            days=match_list[1],
            hours=match_list[2],
            minutes=match_list[3],
            seconds=match_list[4]
        )

        # Used to store the duration that will be displayed later.
        duration_string = ""

        for time_unit in duration:
            if len(duration[time_unit]):
                duration_string += f"{duration[time_unit]} {time_unit} "
                # Update the values for ease of conversion to timedelta object later.
                duration[time_unit] = float(duration[time_unit])
            else:
                # Value defaults to 0 for the unused units of time.
                duration[time_unit] = 0

        # Adds the timedelta of the ban length to the current time to get the unban datetime.
        ban_end_time = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
            days=duration["days"],
            hours=duration["hours"],
            minutes=duration["minutes"],
            seconds=duration["seconds"]
        )

        # Start creating the embed that will be used to alert the moderator that the user was successfully banned.
        embed = embeds.make_embed(ctx=ctx, title=f"Banning user: {user}", thumbnail_url=config.user_ban, color="soft_red")
        embed.description = f"{user.mention} was banned by {ctx.author.mention} for:\n{reason}\n **Duration:** {duration_string}"

        # Attempt to DM the user that they have been banned with various information about their ban. 
        # If the bot was unable to DM the user, adds a notice to the output to let the mod know.
        sent = await self.send_banned_dm_embed(ctx=ctx, user=user, reason=reason, duration=duration_string)
        if not sent:
            embed.add_field(name="Notice:", value=f"Unable to message {user.mention} about this action. This can be caused by the user not being in the server, having DMs disabled, or having the bot blocked.")

        # Bans the user and returns the embed letting the moderator know they were successfully banned.
        await self.ban_member(ctx=ctx, user=user, reason=reason, temporary=True, end_time=ban_end_time.timestamp())
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    """ Load the Ban cog. """
    bot.add_cog(BanCog(bot))
    log.info("Commands loaded: bans")
