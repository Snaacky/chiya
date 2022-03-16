import logging
import re
from chiya.utils import highlights

import discord
from discord.ext import commands


log = logging.getLogger(__name__)


class HighlightsListener(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Scan incoming messages for highlights and notify the subscribed users.
        """
        # Ignore messages from bots (includes itself).
        if message.author.bot:
            return
        
        await highlights.check_highlights(message)
        
def setup(bot: commands.Bot) -> None:
    bot.add_cog(HighlightsListener(bot))
    log.info("Listener loaded: highlights")
