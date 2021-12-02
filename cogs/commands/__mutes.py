import datetime
import logging
import time

import discord
import privatebinapi
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

import utils.duration
from utils import database
from utils import embeds
from utils.config import config
from utils.moderation import can_action_member


log = logging.getLogger(__name__)


class MuteCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    async def mute_member(self, ctx: SlashContext, member: discord.Member, reason: str, temporary: bool = False, end_time: float = None) -> None:
        role = discord.utils.get(ctx.guild.roles, id=config["roles"]["muted"])
        await member.add_roles(role, reason=reason)

        # Open a connection to the database.
        db = database.Database().get()

        # Add the mute to the mod_log database.
        db["mod_logs"].insert(dict(
            user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="mute"
        ))

        # Occurs when the duration parameter in /mute is specified (tempmute).
        if temporary:
            db["timed_mod_actions"].insert(dict(
                user_id=member.id,
                mod_id=ctx.author.id,
                action_type="mute",
                reason=reason,
                start_time=datetime.datetime.now(tz=datetime.timezone.utc).timestamp(),
                end_time=end_time,
                is_done=False
            ))

        # Commit the changes to the database.
        db.commit()
        db.close()

    async def unmute_member(self, member: discord.Member, reason: str, ctx: SlashContext = None) -> None:
        guild = ctx.guild if ctx else self.bot.get_guild(config["guild_id"])
        moderator = ctx.author if ctx else self.bot.user

        # Removes "Muted" role from member.
        role = discord.utils.get(guild.roles, id=config["roles"]["muted"])
        await member.remove_roles(role, reason=reason)

        # Open a connection to the database.
        db = database.Database().get()

        # Add the unmute to the mod_log database.
        db["mod_logs"].insert(dict(
            user_id=member.id, mod_id=moderator.id, timestamp=int(time.time()), reason=reason, type="unmute"
        ))
        tempmute_entry = db["timed_mod_actions"].find_one(user_id=member.id, is_done=False)
        if tempmute_entry:
            db["timed_mod_actions"].update(dict(id=tempmute_entry["id"], is_done=True), ["id"])

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

    async def is_user_muted(self, ctx: SlashContext, member: discord.Member) -> bool:
        if discord.utils.get(ctx.guild.roles, id=config["roles"]["muted"]) in member.roles:
            return True
        return False

    async def send_muted_dm_embed(self, ctx: SlashContext, member: discord.Member, channel: discord.TextChannel, reason: str = None, duration: str = None) -> bool:
        try:
            dm_channel = await member.create_dm()
            embed = embeds.make_embed(
                author=False,
                title="Uh-oh, you've been muted!",
                description="If you believe this was a mistake, contact staff.",
                color=0x8083b0
            )
            embed.add_field(name="Server:", value=f"[{ctx.guild}](https://discord.gg/piracy)", inline=True)
            embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            embed.add_field(name="Length:", value=duration or "Indefinite", inline=True)
            embed.add_field(name="Mute Channel:", value=channel.mention, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/840Q48l.gif")
            return await dm_channel.send(embed=embed)
        except discord.HTTPException:
            return False

    async def send_unmuted_dm_embed(self, member: discord.Member, reason: str, ctx: SlashContext = None) -> bool:
        moderator = ctx.author if ctx else self.bot.user

        # Send member message telling them that they were unmuted and why.
        try:  # In case user has DMs blocked.
            channel = await member.create_dm()
            embed = embeds.make_embed(
                author=False,
                title="Yay, you've been unmuted!",
                description="Review our server rules to avoid being actioned again in the future.",
                color=0x8a3ac5
            )
            embed.add_field(name="Server:", value="[/r/animepiracy](https://discord.gg/piracy)", inline=True)
            embed.add_field(name="Moderator:", value=moderator.mention, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/U5Fvr2Y.gif")
            return await channel.send(embed=embed)
        except discord.HTTPException:
            return False

    async def create_mute_channel(self, ctx: SlashContext, member: discord.Member, reason: str, duration: str = None):
        if not duration:
            duration = "Indefinite"

        # Create a channel in the category specified in the config.
        category = discord.utils.get(ctx.guild.categories, id=config["categories"]["tickets"])
        channel = await ctx.guild.create_text_channel(f"mute-{member.id}", category=category)

        # Give both the staff and the user perms to access the channel.
        await channel.set_permissions(
            discord.utils.get(ctx.guild.roles, id=config["roles"]["trial_mod"]),
            read_messages=True
        )
        await channel.set_permissions(
            discord.utils.get(ctx.guild.roles, id=config["roles"]["staff"]),
            read_messages=True
        )
        await channel.set_permissions(member, read_messages=True)

        # Create embed at the start of the channel letting the user know how long they're muted for and why.
        embed = embeds.make_embed(
            title="🤐 You were muted",
            description="If you have any questions or concerns about your mute, you may voice them here."
        )
        embed.add_field(name="User:", value=member.mention, inline=True)
        embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
        embed.add_field(name="Length:", value=duration, inline=True)
        embed.add_field(name="Reason:", value=reason, inline=False)
        await channel.send(embed=embed)

        # Embed mentions don't count as a ping so this is a workaround to that.
        ping = await channel.send(member.mention)
        await ping.delete()

        return channel

    async def archive_mute_channel(self, user_id: int, reason: str, ctx: SlashContext = None):
        guild = ctx.guild if ctx else self.bot.get_guild(config["guild_id"])
        category = discord.utils.get(guild.categories, id=config["categories"]["tickets"])
        mute_channel = discord.utils.get(category.channels, name=f"mute-{user_id}")

        # Open a connection to the database.
        db = database.Database().get()

        # Gets the most recent mute for the user, sorted by descending (-) ID.
        mute_entry = db["mod_logs"].find_one(user_id=user_id, type="mute", order_by="-id")
        unmute_entry = db["mod_logs"].find_one(user_id=user_id, type="unmute", order_by="-id")
        muter = await self.bot.fetch_user(mute_entry["mod_id"])
        unmuter = await self.bot.fetch_user(unmute_entry["mod_id"])

        db.close()

        # Get the member object of the ticket creator.
        member = await self.bot.fetch_user(user_id)

        # Initialize the PrivateBin message log string.
        message_log = (
            f"Muted User: {member} ({member.id})\n\n"
            f"Muted By: {muter} ({muter.id})\n"
            f"Mute Reason: {mute_entry['reason']}\n\n"
            f"Unmuted By: {unmuter} ({unmuter.id})\n"
            f"Unmute Reason: {reason}\n\n"
        )

        # Initialize a list of moderator IDs as a set for no duplicates.
        mod_list = set()

        # Add the original muting moderator to avoid a blank embed field if no one interacts.
        mod_list.add(muter)

        # Fetch the staff and trial mod role.
        role_staff = discord.utils.get(guild.roles, id=config["roles"]["staff"])
        role_trial_mod = discord.utils.get(guild.roles, id=config["roles"]["trial_mod"])

        # TODO: Implement so it gets the channel when the moderator is the bot
        # Loop through all messages in the ticket from old to new.
        async for message in mute_channel.history(oldest_first=True):
            # Ignore the bot replies.
            if not message.author.bot:
                # Pretty print the time tag into a more digestible format.
                formatted_time = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                # Append the new messages to the current log as we loop.
                message_log += f"[{formatted_time}] {message.author}: {message.content}\n"
                # Iterates only through members that is still in the server.
                if isinstance(message.author, discord.Member):
                    # If the messenger has either staff role or trial mod role, add their ID to the mod_list set.
                    if role_staff in message.author.roles or role_trial_mod in message.author.roles:
                        mod_list.add(message.author)

        # Dump message log to PrivateBin. This returns a dictionary, but only the url is needed for the embed.
        url = privatebinapi.send(config["privatebin"]["url"], text=message_log, expiration="never")["full_url"]

        # Get the amount of time elapsed since the user was muted.
        time_delta = datetime.datetime.utcnow() - mute_channel.created_at
        days = time_delta.days

        # Hours are the time delta in seconds divided by 3600.
        hours, remainder = divmod(time_delta.seconds, 3600)

        # Minutes are the hour remainder divided by 60. The minutes remainder are the seconds.
        minutes, seconds = divmod(remainder, 60)

        # String that will store the duration in a more digestible format.
        elapsed_time = ""
        duration = dict(
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )

        for time_unit in duration:
            # If the time value is 0, skip it.
            if duration[time_unit] == 0:
                continue
            # If the time value is 1, make the time unit into singular form.
            if duration[time_unit] == 1:
                elapsed_time += f"{duration[time_unit]} {time_unit[:-1]} "
            else:
                elapsed_time += f"{duration[time_unit]} {time_unit} "

        # Create the embed in #mute-log.
        embed = embeds.make_embed(
            title=f"{mute_channel.name} archived",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color="blurple"
        )

        embed.add_field(name="Muted User:", value=member.mention, inline=True)
        embed.add_field(name="Muted By:", value=muter.mention, inline=True)
        embed.add_field(name="Unmuted By:", value=unmuter.mention, inline=True)
        embed.add_field(name="Mute Reason:", value=mute_entry['reason'], inline=False)
        embed.add_field(name="Unmute Reason:", value=reason, inline=False)
        embed.add_field(name="Duration:", value=elapsed_time, inline=False)
        embed.add_field(name="Participating Moderators:", value=" ".join(mod.mention for mod in mod_list), inline=False)
        embed.add_field(name="Mute Log: ", value=url, inline=False)

        # Send the embed to #mute-log.
        mute_log = discord.utils.get(guild.channels, id=config["channels"]["mute_log"])
        await mute_log.send(embed=embed)

        # Delete the mute channel.
        await mute_channel.delete()

    @cog_ext.cog_slash(
        name="mute",
        description="Mutes a member in the server",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="member",
                description="The member that will be muted",
                option_type=6,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the member is being muted",
                option_type=3,
                required=True
            ),
            create_option(
                name="duration",
                description="The length of time the user will be muted for",
                option_type=3,
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
    async def mute(self, ctx: SlashContext, member: discord.Member, reason: str, duration: str = None):
        """ Mutes member in guild. """
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        # Checks if invoker can action that member (self, bot, etc.)
        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        # Check if the user is muted already.
        if await self.is_user_muted(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"{member.mention} is already muted.")

        # Discord caps embed fields at a ridiculously low character limit, avoids problems with future embeds.
        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        # If the duration is not specified, default it to a permanent mute.
        if not duration:
            # Start creating the embed that will be used to alert the moderator that the user was successfully muted.
            embed = embeds.make_embed(
                ctx=ctx,
                title=f"Muting member: {member.name}",
                description=f"{member.mention} was muted by {ctx.author.mention} for: {reason}",
                thumbnail_url="https://i.imgur.com/rHtYWIt.png",
                color="soft_red",
            )

            # Create the mute channel in the Staff category.
            channel = await self.create_mute_channel(ctx=ctx, member=member, reason=reason)

            # Attempt to DM the user to let them know they were muted.
            if not await self.send_muted_dm_embed(ctx=ctx, member=member, channel=channel, reason=reason):
                embed.add_field(
                    name="Notice:",
                    value=(
                        f"Unable to message {member.mention} about this action. "
                        "This can be caused by the user not being in the server, "
                        "having DMs disabled, or having the bot blocked."
                    )
                )

            # Mutes the user and returns the embed letting the moderator know they were successfully muted.
            await self.mute_member(ctx=ctx, member=member, reason=reason)
            return await ctx.send(embed=embed)

        # Get the duration string for embed and mute end time for the specified duration.
        duration_string, mute_end_time = utils.duration.get_duration(duration=duration)
        # If the duration string is empty due to Regex not matching anything, send and error embed and return.
        if not duration_string:
            return await embeds.error_message(
                ctx=ctx,
                description=(
                    "Duration syntax: `#d#h#m#s` (day, hour, min, sec)\n"
                    "You can specify up to all four but you only need one."
                )
            )

        # Start creating the embed that will be used to alert the moderator that the user was successfully muted.
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Muting member: {member}",
            thumbnail_url="https://i.imgur.com/rHtYWIt.png",
            color="soft_red"
        )
        embed.description = f"{member.mention} was muted by {ctx.author.mention} for: {reason}"
        embed.add_field(name="Duration:", value=duration_string, inline=False)

        # Create the mute channel in the Staff category.
        channel = await self.create_mute_channel(ctx=ctx, member=member, reason=reason, duration=duration_string)

        # Attempt to DM the user to let them know they were muted.
        if not await self.send_muted_dm_embed(
            ctx=ctx,
            member=member,
            channel=channel,
            reason=reason,
            duration=duration_string
        ):
            embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                )
            )

        # Mutes the user and stores the unmute time in the database for the background task.
        await self.mute_member(
            ctx=ctx,
            member=member,
            reason=reason,
            temporary=True,
            end_time=mute_end_time
        )
        await ctx.send(embed=embed)

    @cog_ext.cog_slash(
        name="unmute",
        description="Unmutes a member in the server",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="member",
                description="The member that will be unmuted",
                option_type=6,
                required=True
            ),
            create_option(
                name="reason",
                description="The reason why the member is being unmuted",
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
    async def unmute(self, ctx: SlashContext, member: discord.Member, reason: str):
        """ Unmutes member in guild. """
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        # Checks if invoker can action that member (self, bot, etc.)
        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        # Check if the user is not muted already.
        if not await self.is_user_muted(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"{member.mention} is not muted.")

        # Discord caps embed fields at a ridiculously low character limit, avoids problems with future embeds.
        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        # Start creating the embed that will be used to alert the moderator that the user was successfully unmuted.
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Unmuting member: {member.name}",
            color="soft_green",
            thumbnail_url="https://i.imgur.com/W7DpUHC.png"
        )
        embed.description = f"{member.mention} was unmuted by {ctx.author.mention} for: {reason}"

        # Execution order is important here, otherwise the wrong unmuter will be used in the embed.
        await self.unmute_member(ctx=ctx, member=member, reason=reason)
        await self.archive_mute_channel(ctx=ctx, user_id=member.id, reason=reason)

        # Attempt to DM the user to let them and the mods know they were unmuted.
        if not await self.send_unmuted_dm_embed(ctx=ctx, member=member, reason=reason):
            embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                )
            )

        # If the mod sent the /unmute in the mute channel, this will cause a errors.NotFound 404.
        # We cannot send the embed and then archive the channel because that will cause a error.AlreadyResponded.
        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            pass


def setup(bot: Bot) -> None:
    bot.add_cog(MuteCog(bot))
    log.info("Commands loaded: mutes")
