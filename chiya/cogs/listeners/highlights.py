import datetime
import logging
import re

import discord
import orjson
from discord.ext import commands

from chiya import database
from chiya.utils import embeds


log = logging.getLogger(__name__)


class HighlightsListener(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        db = database.Database().get()
        self.highlights = [
            {"term": highlight["term"], "users": orjson.loads(highlight["users"])}
            for highlight in db["highlights"].find()
        ]

    def refresh_highlights(self):
        db = database.Database().get()
        self.highlights = [
            {"term": highlight["term"], "users": orjson.loads(highlight["users"])}
            for highlight in db["highlights"].find()
        ]

    async def is_user_active(self, channel: discord.TextChannel, member: discord.Member) -> bool:
        """
        Checks if the user was active in chat recently.
        """
        after = datetime.datetime.now() - datetime.timedelta(minutes=20)
        messages = await channel.history(after=after).flatten()
        for historical_message in messages:
            if historical_message.author == member:
                return True

        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Scan incoming messages for highlights and notify the subscribed users.
        """
        # Ignore messages from bots (includes itself).
        if message.author.bot:
            return

        for highlight in self.highlights:
            regex = r"\b" + highlight["term"] + r"\b"
            result = re.search(regex, message.clean_content, re.IGNORECASE)
            if result:
                # caught a term
                messages = await message.channel.history(limit=4, before=message).flatten()
                messages_str = ""
                for past_message in reversed(messages):
                    messages_str += f"**[<t:{int(past_message.created_at.timestamp())}:T>] {past_message.author.name}:** {past_message.clean_content[0:256]}\n"
                messages_str += f"⭐️ **[<t:{int(message.created_at.timestamp())}:T>] {message.author.name}:** {message.clean_content[0:256]}\n"
                embed = embeds.make_embed(
                    title=highlight["term"],
                    description=messages_str,
                    color=discord.Color.gold(),
                )
                embed.add_field(name="Source Message", value=f"[Jump to]({message.jump_url})")
                for subscriber in highlight["users"]:
                    if subscriber == message.author.id:
                        continue
                    member = message.guild.get_member(subscriber)
                    if not member:
                        member = await message.guild.fetch_member(subscriber)
                    if not message.channel.permissions_for(member).view_channel:
                        continue
                    if await self.is_user_active(message.channel, member):
                        continue
                    try:
                        channel = await member.create_dm()
                        await channel.send(
                            content=f"You were mentioned with the highlight term `{highlight['term']}` in **{message.guild.name}** {message.channel.mention}.",
                            embed=embed,
                        )
                    except Exception:
                        pass


def setup(bot: commands.Bot) -> None:
    bot.add_cog(HighlightsListener(bot))
    log.info("Listener loaded: highlights")
