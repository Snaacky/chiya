import itertools
import logging
import os
import time

import dataset
import discord
from discord.ext import commands

import config
import utils.database
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class ModerationCog(commands.Cog):
    """ModerationCog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="ban")
    async def ban_member(self, ctx, user, reason: str, delete_message_days: int = 0):
        """ Bans user from guild """
        member = await commands.converter.UserConverter().convert(ctx, user)

        if member is None:
            raise commands.UserNotFound(user)

        # Stop user from banning themselves.
        if ctx.author.id == member.id:
            await ctx.reply("You cannot ban yourself!")
            return  # TODO: Implement error embed here.

        # Stop user from trying to ban Chiya (not that it's possible).
        if self.bot.user.id == member.id:
            await ctx.reply("... Excuse me?")
            return  # TODO: Implement error embed here.

        # For some reason, Discord lets you .ban() an already banned person without error.
        try:
            ban = await ctx.guild.fetch_ban(member)
            if ban:
                await ctx.reply("That user is already banned!")
                return  # TODO: Implement error embed here.
        except discord.errors.NotFound:
            pass

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.ban
        await ctx.guild.ban(user=member, reason=reason, delete_message_days=delete_message_days)

        # Add the ban to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="ban"
            ))

        # TODO: Add DM letting the user know they were banned and the reason.
        await ctx.reply(f"Banned {member} for {reason}")
        # TODO: Return successfully banned user embed.

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="unban")
    async def unban_member(self, ctx, user, reason: str):
        """ Unbans user from guild """
        member = await commands.converter.UserConverter().convert(ctx, user)

        if member is None:
            raise commands.UserNotFound(user)

        if ctx.author.id == member.id:
            await ctx.reply("You cannot unban yourself!")
            return  # TODO: Implement error embed here.

        # Check to see if the user is actually banned.
        try:
            await ctx.guild.fetch_ban(member)
        except discord.errors.NotFound:
            await ctx.reply("Unable to find ban for that user!")
            return  # TODO: Implement error embed here.

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.unban
        await ctx.guild.unban(user=member, reason=reason)

        # Add the unban to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="unban"
            ))

        await ctx.reply(f"Unbanned {member} for {reason}")

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="kick")
    async def kick_member(self, ctx, user, reason: str):
        """ Kicks user from guild. """
        member = await commands.converter.UserConverter().convert(ctx, user)
        if member is None:
            raise commands.UserNotFound(user)

        if ctx.author.id == member.id:
            await ctx.reply("You cannot unban yourself!")
            return  # TODO: Implement error embed here

        # Stop user from trying to kick Chiya (not that it's possible).
        if self.bot.user.id == member.id:
            await ctx.reply("... Excuse me?")
            return  # TODO: Implement error embed here.

        if ctx.guild.fetch_member(member) is None:
            await ctx.reply("That user is not in the server.")
            return  # TODO: Implement error embed here.

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.kick
        await ctx.guild.kick(user=member, reason=reason)

        # Add the kick to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="kick"
            ))
        
        # Respond to the context that the user was kicked.
        await ctx.reply(f"Kicked {member} for {reason}")
        # TODO: Return successfully kicked user embed.
        # TODO: Add DM letting the user know they were banned and the reason.
        return NotImplementedError

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="mute")
    async def mute(self, ctx):
        return NotImplementedError

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="unmute")
    async def unmute(self, ctx):
        return NotImplementedError

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="warn")
    async def warn(self, ctx, user, *reason: str):
        """ Kicks user from guild. """
        member = await commands.converter.UserConverter().convert(ctx, user)
        if member is None:
            raise commands.UserNotFound(user)
        
        # TODO: Uncomment this, temporarily disabled for testing!
        # if ctx.author.id == member.id:
        #    await ctx.reply("You cannot warn yourself!")
        #    return  # TODO: Implement error embed here

        if ctx.guild.fetch_member(member) is None:
            await ctx.reply("That user is not in the server.")
            return  # TODO: Implement error embed here.

        # Converts reason from a list of strings into a full sentence string.
        reason = " ".join(reason)
        
        # Attempts to creates the DM channel in case the bot hasn't interacted with the user before.
        channel = await member.create_dm()
        await channel.send(f"""
        You received a warning in {ctx.guild.name}!
        
Reason: {reason}

You do not have to acknowledge or respond to this warning but please keep in mind that contentious bad behavior will result in more severe punishment in the future.
""")  # TODO: Replace with an embed!

        # Add the warning to the mod_log database.
        with dataset.connect(utils.database.get_db()) as tx:
            tx["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="warn"
            ))
        
        # Respond to the context that the user was kicked.
        await ctx.reply(f"Warned {member} for {reason}")
        # TODO: Return successfully kicked user embed.

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="notes")
    async def notes(self, ctx):
        return NotImplementedError

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="addnote")
    async def add_note(self, ctx):
        return NotImplementedError

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


# The setup function below is necessary. Remember we give bot.add_cog() the name of the class in this case SimpleCog.
# When we load the cog, we use the name of the file.
def setup(bot) -> None:
    """ Load the ModerationCog cog. """
    bot.add_cog(ModerationCog(bot))
    log.info("Cog loaded: ModerationCog")
