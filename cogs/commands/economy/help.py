import logging

from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext

from utils import embeds
from utils.config import config
from utils.record import record_usage

log = logging.getLogger(__name__)


class HelpCog(Cog):
    """Help command cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="help",
        description="Detailed information about the economy",
        guild_ids=config["guild_ids"],
    )
    async def help(self, ctx: SlashContext):
        """Help command to view the detailed information about the economy system."""
        await ctx.defer()

        # Warn if the command is called outside of #bots channel. Using a tuple is more memory efficient.
        if ctx.channel.id not in (
            config["channels"]["bots"],
            config["channels"]["bot_testing"],
        ):
            return await embeds.error_message(ctx=ctx, description="This command can only be run in #bots channel.")

        embed = embeds.make_embed(title="Economy details", color="green")
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        buffer = (
            "Your experience point, gained mainly by participating in conversations. Short messages will give less buffer, "
            "while longer messages will receive an added bonus.\n"
            "Note that your message count and buffer gain will be reverted if your message is either deleted by you or a moderator. "
            "Edited messages will have its buffer gain recalculated accordingly.\n The unit being used is MB, where "
            "1024 MB = 1 GB, and 1024 GB = 1 TB."
        )
        embed.add_field(name="​", value=f"✨ **Buffer:** {buffer}", inline=False)

        uploads = (
            "Your message count in this server. Does not count your messages retroactively before the system exists."
        )
        embed.add_field(name="​", value=f"✨ **Upload:** {uploads}", inline=False)

        user_class = (
            "Your rank on the server. There are 8 ranks in total, where:\n\n"
            "__Member__: The default rank.\n\n"
            "__User__: The next rank after 'Member'. Requires 10240 MB (10 GB) buffer and 1000 uploads.\n\n"
            "__Power User__: /buy color and /buy role commands are unlocked. Requires 25600 MB (25 GB) buffer and 2500 uploads.\n\n"
            "__Elite__: The next rank after 'Power User'. Requires 51200 MB (50 GB) buffer and 5000 uploads.\n\n"
            "__Torrent Master__: The next rank after 'Elite'. Requires 102400 MB (100 GB) buffer and 10000 uploads.\n\n"
            "__Power TM__: Abbreviation of 'Power Torrent Master'. Requires 256000 MB (250 GB) buffer and 22500 uploads.\n\n"
            "__Elite TM__: Abbreviation of 'Elite Torrent Master'. Requires 512000 MB (500 GB) buffer and 45000 uploads.\n\n"
            "__Legend__: The legendary realm reserved for the most based pirates. Requires 1048576 MB (1 TB) buffer and 80000 uploads."
        )
        embed.add_field(name="​", value=f"✨ **User class:** {user_class}", inline=False)

        store = "Purchase various server-specific upgrades with /buy commands. See /commands for more details."
        embed.add_field(name="​", value=f"✨ **The store system:** {store}", inline=False)

        color_packs = (
            "Based on the HSV color system with 3 primary (red, green, blue) hues and 3 secondary (yellow, cyan, magenta) hues. "
            "The more color packs you own, the broader the range of hues you can roll using /buy color.\n\n"
            "For a more detailed explanation, visit this article: "
            "http://learn.leighcotnoir.com/artspeak/elements-color/hue-value-saturation/"
        )
        embed.add_field(name="​", value=f"✨ **Color packs:** {color_packs}", inline=False)

        saturation = (
            "Based on the HSV color system. The higher the saturation level, the better the chance you can roll colors with "
            "a higher intensity"
        )
        embed.add_field(name="​", value=f"✨ **Saturation:** {saturation}", inline=False)

        brightness = "Based on the HSV color system. The higher the brightness level, the better the chance you can roll a less dark color."
        embed.add_field(name="​", value=f"✨ **Brightness:** {brightness}", inline=False)

        vouch = (
            "Earned by having other members using /vouch on you for helping them out, typically by answering questions. The vouched "
            "person will also receive a small amount of buffer as a reward. A 'Helpful' role will be awarded after receiving 50 vouches."
        )
        embed.add_field(name="​", value=f"✨ **Vouch:** {vouch}", inline=False)

        freeleech_token = (
            "Earned on every unique user class promotion and special occasions such as holidays or anniversaries. Those "
            "tokens will allow you to purchase anything from the store at no cost!"
        )
        embed.add_field(name="​", value=f"✨ **Freeleech token:** {freeleech_token}", inline=False)

        custom_role = (
            "Your custom role, which can be bought from the store if your user class is Power User or above, and can be "
            "deterministically customized except its color. See /commands for more info about the customization commands."
        )
        embed.add_field(name="​", value=f"✨ **Custom role:** {custom_role}", inline=False)

        achievement = (
            "Your achievements in this server by meeting specific criteria. It could be something simple, but could also be "
            "something hidden in plain sight, or awarded for making a meaningful contribution and recognized by the staff team. "
            "However, don't spoil them and ruin the fun!"
        )
        embed.add_field(name="​", value=f"✨ **Achievement:** {achievement}", inline=False)

        await ctx.send(embed=embed)

    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="commands",
        description="Detailed information about the economy",
        guild_ids=config["guild_ids"],
    )
    async def commands(self, ctx: SlashContext):
        """Help command to view a list of user commands."""
        await ctx.defer()

        # Warn if the command is called outside of #bots channel. Using a set is faster than a tuple.
        if ctx.channel.id not in (
            config["channels"]["bots"],
            config["channels"]["bot_testing"],
        ):
            return await embeds.error_message(ctx=ctx, description="This command can only be run in #bots channel.")

        embed = embeds.make_embed(title="Economy commands", color="green")
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        daily = "Receive a random amount of buffer (5 rarities) once every 20 hours."
        embed.add_field(name="​", value=f"✨ **/daily:** {daily}", inline=False)

        buy_role = (
            "Purchase a colorless custom role with a determined name for your user profile. Costs 10 GB buffer.\n"
            "**role_name**: The name to be assigned to the role.\n"
            "**freeleech**: Enable freeleech for this item once, costing 5 freeleech tokens."
        )
        embed.add_field(name="​", value=f"✨ **/buy role:** {buy_role}", inline=False)

        buy_color = (
            "Rolls a random color for your custom role, affected by your purchased upgrades (color packs, "
            "brightness, and saturation). Costs 64 MB buffer per roll.\n"
            "**freeleech**: Enable freeleech for this item once, costing 1 freeleech token."
        )
        embed.add_field(name="​", value=f"✨ **/buy color:** {buy_color}", inline=False)

        buy_nickname = (
            "Purchase a nickname for 256 MB buffer.\n"
            "**nickname**: The new nickname to be changed to.\n"
            "**freeleech**: Enable freeleech for this item once for 1 freeleech token."
        )
        embed.add_field(name="​", value=f"✨ **/buy nickname:** {buy_nickname}", inline=False)

        upgrade_daily = (
            "Increases the chance to receive double the amount of buffer from /daily. Each level gives +0.35%, "
            "capped out at +35%. Costs +5 MB buffer per level.\n"
            "**amount**: The number of levels to be purchased.\n"
            "**freeleech**: Enable freeleech for this item once, costing 1 freeleech token per level."
        )
        embed.add_field(name="​", value=f"✨ **/upgrade daily:** {upgrade_daily}", inline=False)

        upgrade_hue = (
            "Increases the range of colors that can be rolled with /buy color. Costs 3 GB per color pack.\n"
            "**pack**: One or more of the following options: red, yellow, green, cyan, blue, magenta.\n"
            "**freeleech**: Enable freeleech for this item, costing 2 freeleech tokens."
        )
        embed.add_field(name="​", value=f"✨ **/upgrade hue:** {upgrade_hue}", inline=False)

        upgrade_saturation = (
            "Allows more saturated colors to be rolled with /buy color. Costs +3 MB buffer per level.\n"
            "**amount**: The number of levels to be purchased.\n"
            "**freeleech**: Enable freeleech for this item once, costing 1 freeleech token per level."
        )
        embed.add_field(
            name="​",
            value=f"✨ **/upgrade saturation:** {upgrade_saturation}",
            inline=False,
        )

        upgrade_value = (
            "Allows brighter colors to be rolled with /buy color. Costs +3 MB buffer per level.\n"
            "**amount**: The number of levels to be purchased.\n"
            "**freeleech**: Enable freeleech for this item once, costing 1 freeleech token per level."
        )
        embed.add_field(name="​", value=f"✨ **/upgrade brightness:** {upgrade_value}", inline=False)

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    """Load the Help cog."""
    bot.add_cog(HelpCog(bot))
    log.info("Commands loaded: help")
