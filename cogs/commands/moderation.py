import datetime
import logging
import time


import dataset
import discord
from discord.ext import commands

import constants
import utils.database
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class ModerationCog(commands.Cog):
    """ModerationCog"""

    def __init__(self, bot):
        self.bot = bot

    async def can_action_user(self, ctx, member):
        """ Stop mods from doing stupid things. """
        # Stop mods from actioning themselves or the bot.
        if member.id == ctx.author.id or member.id == self.bot.user.id:
            await ctx.reply("You cannot action that user.")
            return False

        # Stop mods from actioning one another or people higher ranked than them.
        member = await ctx.guild.fetch_member(member.id) 
        if member.top_role >= ctx.author.top_role:
            await ctx.reply("You cannot action that user.")
            return False

        # Otherwise, the action is probably valid, return true.
        return True

    @commands.has_role("Staff")
    @commands.before_invoke(record_usage)
    @commands.command(name="ban")
    async def ban_member(self, ctx, user, *reason: str, delete_message_days: int = 0):
        """ Bans user from guild """
        member = await commands.converter.UserConverter().convert(ctx, user)

        # The user specified doesn't exist.
        if member is None:
            raise commands.UserNotFound(user)

        # Checks if invoker can action that user (self, bot, etc.)
        if not await self.can_action_user(ctx, member):
            return

        # For some reason, Discord lets you .ban() an already banned person without error.
        try:
            ban = await ctx.guild.fetch_ban(member)
            if ban:
                await ctx.reply("That user is already banned!")
                return
        except discord.errors.NotFound:
            pass

        # Converts reason from a list of strings into a full sentence string.
        reason = " ".join(reason)

        # Throw an error if the mod left the reason empty.
        if not reason:
            await ctx.reply("You did not specify a reason.")
            return

        # Send user message telling them that they were banned and why.
        channel = await member.create_dm()
        message = f"You were banned from {ctx.guild} for: {reason}"
        await channel.send(message)

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.ban
        await ctx.guild.ban(user=member, reason=reason, delete_message_days=delete_message_days)

        # Add the ban to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="ban"
            ))

        await ctx.reply(f"Banned {member}")

    @commands.has_role("Staff")
    @commands.before_invoke(record_usage)
    @commands.command(name="unban")
    async def unban_member(self, ctx, user, *reason: str):
        """ Unbans user from guild """
        member = await commands.converter.UserConverter().convert(ctx, user)

        if member is None:
            raise commands.UserNotFound(user)

        # Checks if invoker can action that user (self, bot, etc.)
        if not await self.can_action_user(ctx, member):
            return

        # Check to see if the user is actually banned.
        try:
            await ctx.guild.fetch_ban(member)
        except discord.errors.NotFound:
            await ctx.reply("Unable to find a ban for that user!")
            return 

        # Converts reason from a list of strings into a full sentence string.
        reason = " ".join(reason)

        # Throw an error if the mod left the reason empty.
        if not reason:
            await ctx.reply("You did not specify a reason.")
            return

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.unban
        await ctx.guild.unban(user=member, reason=reason)

        # Add the unban to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="unban"
            ))

        await ctx.reply(f"Unbanned {member}")

    @commands.has_role("Staff")
    @commands.before_invoke(record_usage)
    @commands.command(name="kick")
    async def kick_member(self, ctx, user, *reason: str):
        """ Kicks user from guild. """
        member = await commands.converter.UserConverter().convert(ctx, user)
        if member is None:
            raise commands.UserNotFound(user)

        # Checks if invoker can action that user (self, bot, etc.)
        if not await self.can_action_user(ctx, member):
            return

        # User is not currently in the guild.
        if await ctx.guild.fetch_member(member.id) is None:
            raise commands.UserNotFound(user)

        # Converts reason from a list of strings into a full sentence string.
        reason = " ".join(reason)

        # Throw an error if the mod left the reason empty.
        if not reason:
            await ctx.reply("You did not specify a reason.")
            return

        # Send user message telling them that they were kicked and why.
        channel = await member.create_dm()
        message = f"You were kicked from {ctx.guild} for: {reason}"
        await channel.send(message)

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.kick
        await ctx.guild.kick(user=member, reason=reason)

        # Add the kick to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="kick"
            ))

        await ctx.reply(f"Kicked {member}")

    @commands.has_role("Staff")
    @commands.before_invoke(record_usage)
    @commands.command(name="mute")
    async def mute(self, ctx, user, *reason: str):
        # TODO: Implement temp/timed mute functionality
        member = await commands.converter.UserConverter().convert(ctx, user)
        if member is None:
            raise commands.UserNotFound(user)

        # Checks if invoker can action that user (self, bot, etc.)
        if not await self.can_action_user(ctx, member):
            return

        # User is not currently in the guild.
        if await ctx.guild.fetch_member(member.id) is None:
            raise commands.UserNotFound(user)

        # Converts reason from a list of strings into a full sentence string.
        reason = " ".join(reason)

        # Throw an error if the mod left the reason empty.
        if not reason:
            await ctx.reply("You did not specify a reason.")
            return

        # Adds "Muted" role to user.
        # TODO: Add role name to configuration, maybe by ID?
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        user = await ctx.guild.fetch_member(member.id)
        await user.add_roles(role)

        # Send user message telling them that they were muted and why.
        channel = await member.create_dm()
        message = f"You were muted in {ctx.guild} for: {reason}"
        await channel.send(message)

        # Add the mute to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="mute"
            ))

        await ctx.reply(f"Muted {member}")

    @commands.has_role("Staff")
    @commands.before_invoke(record_usage)
    @commands.command(name="unmute")
    async def unmute(self, ctx, user, *reason: str):
        member = await commands.converter.UserConverter().convert(ctx, user)
        if member is None:
            raise commands.UserNotFound(user)

        # Checks if invoker can action that user (self, bot, etc.)
        if not await self.can_action_user(ctx, member):
            return

        # User is not currently in the guild.
        if await ctx.guild.fetch_member(member.id) is None:
            raise commands.UserNotFound(user)

        # Converts reason from a list of strings into a full sentence string.
        reason = " ".join(reason)

        # Throw an error if the mod left the reason empty.
        if not reason:
            await ctx.reply("You did not specify a reason.")
            return

        # Removes "Muted" role from user.
        # TODO: Add role name to configuration, maybe by ID?
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        user = await ctx.guild.fetch_member(member.id)
        await user.remove_roles(role)

        # Send user message telling them that they were banned and why.
        channel = await member.create_dm()
        message = f"You were unmuted in {ctx.guild}. Try to behave in the future!"
        await channel.send(message)

        # Add the mute to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="unmute"
            ))

        await ctx.reply(f"Unmuted {member}")

    @commands.has_role("Staff")
    @commands.before_invoke(record_usage)
    @commands.command(name="warn")
    async def warn(self, ctx, user, *reason: str):
        """ Sends user a warning DM and logs to database. """
        member = await commands.converter.UserConverter().convert(ctx, user)
        if member is None:
            raise commands.UserNotFound(user)

        # User is not currently in the guild.
        if await ctx.guild.fetch_member(member.id) is None:
            raise commands.UserNotFound(user)

        # Converts reason from a list of strings into a full sentence string.
        reason = " ".join(reason)

        if not reason:
            await ctx.reply("You did not specify a reason.")
            return

        # Send user message telling them that they were warned and why.
        channel = await member.create_dm()
        message = f"You were warned in {ctx.guild} for: {reason}"
        await channel.send(message)

        # Add the warning to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="warn"
            ))

        # Respond to the context that the user was kicked.
        await ctx.reply(f"Warned {member} for {reason}")
        # TODO: Return successfully kicked user embed.

    @commands.has_role("Staff")
    @commands.before_invoke(record_usage)
    @commands.command(name="addnote")
    async def add_note(self, ctx, user, *note):
        """ Adds a moderator note to a user. """
        member = await commands.converter.UserConverter().convert(ctx, user)
        if member is None:
            raise commands.UserNotFound(user)

        # User is not currently in the guild.
        if await ctx.guild.fetch_member(member.id) is None:
            raise commands.UserNotFound(user)

        # Converts reason from a list of strings into a full sentence string.
        note = " ".join(note)

        # Prevent the user from using the command without providing a reason.
        if not note:
            await ctx.reply("You must enter a reason.")
            return

        # Add the note to the mod_notes database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_notes"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), note=note
            ))

        # Respond to the context that the user was kicked.
        await ctx.reply(f"Added note to {member}.")
        # TODO: Return successfully kicked user embed.

    @commands.is_owner()
    @commands.before_invoke(record_usage)
    @commands.command(name="rules")
    async def rules(self, ctx):
        """ Generates the #rules channel embeds. """
        embed = discord.Embed(colour=discord.Colour(0x2f3136))
        embed.set_image(url="https://i.imgur.com/Yk4kwZy.gif")
        await ctx.send(embed=embed)

        embed = discord.Embed(
            title="Rule #1: Do not send copyright infringing content.",
            description="Posting copyright infringing material including streams, torrents, downloads, or Discord file uploads are forbidden by Discord's terms of service and will be removed.")
        await ctx.send(embed=embed)

        embed = discord.Embed(
            title="Rule #2: Do not harass other users.",
            description="Please be courteous and respectful to your fellow server members. We will not tolerate harassment or personal attacks in our community.")
        await ctx.send(embed=embed)

        embed = discord.Embed(
            title="Rule #3: Do not spam.",
            description="Spamming is strictly forbidden. This includes but is not limited to: large walls of text, copypasta, and/or repetitive message spam.")
        await ctx.send(embed=embed)

        embed = discord.Embed(
            title="Rule #4: Do not send NSFW content outside of NSFW channels.",
            description="NSFW content is only allowed in channels marked as NSFW. You can opt-in to our NSFW channel through the #gate. NSFL content is not allowed.")
        await ctx.send(embed=embed)

        embed = discord.Embed(
            title="Rule #5: Do not post unmarked spoilers.",
            description="All spoilers or potential spoilers must be marked as a spoiler. Instructions on how to use Discord spoilers can be found [here](https://support.discord.com/hc/en-us/articles/360022320632-Spoiler-Tags-).")
        await ctx.send(embed=embed)

        embed = discord.Embed(
            title="Rule #6: Do not advertise without permission.",
            description="All promotional content must be approved beforehand by the mod team. This includes websites, apps, social media, etc. We do not allow advertising through DMs under any circumstances.")
        await ctx.send(embed=embed)

        embed = discord.Embed(
            title="Rule #7: Do not request or B/S/T invites.",
            description="Do not request, buy, sell, trade, or publicly give away invites for private communities through our server. Any of the above actions is a bannable offense in most private communities.")
        await ctx.send(embed=embed)

        await ctx.send("https://discord.gg/piracy")
        await ctx.send("https://piracy.moe")
        await ctx.message.delete()


# The setup function below is necessary. Remember we give bot.add_cog() the name of the class in this case SimpleCog.
# When we load the cog, we use the name of the file.
def setup(bot) -> None:
    """ Load the ModerationCog cog. """
    bot.add_cog(ModerationCog(bot))
    log.info("Cog loaded: ModerationCog")
