"""
This File is for demonstrating and used as a template for future cogs.
"""

import logging
import discord

from discord.ext import commands
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
        
        if ctx.author.id == member.id:
            await ctx.send("are you retarded")
            return  # TODO: Implement error embed here

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.ban
        await ctx.guild.ban(member, delete_message_days, reason)
        await ctx.send(f"Banned {member} by {ctx.author} for {reason}")

        # TODO: Log to database.
        # TODO: Return successfully banned user embed.
        return NotImplementedError

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="unban")
    async def unban_member(self, ctx, user, reason: str):
        """ Unbans user from guild """
        member = await commands.converter.UserConverter().convert(ctx, user)

        if member is None:
            raise commands.UserNotFound(user)
        
        if ctx.author.id == member.id:
            await ctx.send("are you retarded")
            return  # TODO: Implement error embed here

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.unban
        await ctx.guild.unban(user=member, reason=reason)
        await ctx.send(f"Unbanned {member} by {ctx.author} for {reason}")
        # TODO: Log to database.
        # TODO: Return successfully unbanned user embed.
        return NotImplementedError

    @commands.has_role("Discord Mod")
    @commands.before_invoke(record_usage)
    @commands.command(name="kick")
    async def kick_member(self, ctx, user, reason: str):
        """Kicks user from guild."""
        member = await commands.converter.UserConverter().convert(ctx, user)
        if member is None:
            raise commands.UserNotFound(user)
        
        if ctx.author.id == member.id:
            await ctx.send("are you retarded")
            return  # TODO: Implement error embed here
            

        if member.roles in await commands.converter.RoleConverter().convert(ctx, "Discord Mod"):
            # does this even work?
            await ctx.send("This works!")
        else:
            await ctx.send("doesn't work. 😢")

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.kick
        await ctx.guild.kick(user=member, reason=reason)
        await ctx.send(f"Kicked {member} by {ctx.author} for {reason}")
        # TODO: Log to database.
        # TODO: Return successfully kicked user embed.
        return NotImplementedError

    @commands.before_invoke(record_usage)
    @commands.command(name="mute")
    async def mute(self, ctx):
        return NotImplementedError
    
    @commands.before_invoke(record_usage)
    @commands.command(name="unmute")
    async def unmute(self, ctx):
        return NotImplementedError

    @commands.before_invoke(record_usage)
    @commands.command(name="warn")
    async def warn(self, ctx):
        return NotImplementedError

    @commands.before_invoke(record_usage)
    @commands.command(name="notes")
    async def notes(self, ctx):
        return NotImplementedError
    
    @commands.before_invoke(record_usage)
    @commands.command(name="addnote")
    async def add_note(self, ctx):
        return NotImplementedError
    

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
