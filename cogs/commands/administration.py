import logging
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, Greedy

from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class AdministrationCog(Cog):
    """ Administration Cog Cog """

    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="rules")
    async def rules(self, ctx: Context):
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


def setup(bot: Bot) -> None:
    """ Load the AdministrationCog cog. """
    bot.add_cog(AdministrationCog(bot))
    log.info("Cog loaded: AdministrationCog")
