import logging
import re
import orjson

import discord
from discord.ext import commands

from chiya.utils import embeds
from chiya import database, config


log = logging.getLogger(__name__)


class HighlightsListener(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        db = database.Database().get()
        self.highlights = [{"term": highlight['term'], "users": orjson.loads(highlight['users'])} for highlight in db['highlights'].find()]

    def refresh_highlights(self):
        db = database.Database().get()
        self.highlights = [{"term": highlight['term'], "users": orjson.loads(highlight['users'])} for highlight in db['highlights'].find()]

    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Scan incoming messages for highlights and notify the subscribed users.
        """
        # Ignore messages from bots (includes itself).
        if message.author.bot:
            return

        for highlight in self.highlights:
            regex = r"\b" + highlight['term'] + r"\b"
            result = re.search(regex, message.clean_content, re.IGNORECASE)
            if result:
                # caught a term
                embed = embeds.make_embed(
                    title="Highlighted message caught!",
                    description=f"[Message link]({message.jump_url})",
                    color=discord.Color.gold()
                )
                for subscriber in highlight['users']:
                    if subscriber == message.author.id:
                        continue
                    member = message.guild.get_member(subscriber)
                    if not member:
                        member = await message.guild.fetch_member(subscriber)
                    try:
                        channel = await member.create_dm()
                        await channel.send(embed=embed)
                    except Exception:
                        pass


def setup(bot: commands.Bot) -> None:
    bot.add_cog(HighlightsListener(bot))
    log.info("Listener loaded: highlights")
