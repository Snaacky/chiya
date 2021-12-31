import logging
import re

import discord
from discord.ext import commands


log = logging.getLogger(__name__)


class AutomodListener(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Scan incoming messages for problematic content and action
        the message (and the user) accordingly.

        Args:
            message: The current message.
        """
        # Ignores messages from bots (includes itself).
        if message.author.bot:
            return

        # Remove message containing Cyrillic characters (used for bypassing automod).
        if bool(re.search('[\u0400-\u04FF]', message.clean_content)):
            await message.delete()

        # Remove message and ban user if "@everyone" and "nitro" are in the same message (nitro scam behavior).
        if all(match in message.content for match in ["nitro", "@everyone"]):
            await message.delete()
            await message.guild.ban(
                user=message.author,
                reason="Banned by potential Nitro scam link detection",
                delete_message_days=1
            )


def setup(bot: commands.Bot) -> None:
    bot.add_cog(AutomodListener(bot))
    log.info("Listener loaded: automod")
