import datetime
import re

import discord
import orjson
from discord.ext import commands
from loguru import logger as log

from chiya.config import config
from chiya.database import Highlight, Session
from chiya.utils import embeds


class HighlightListeners(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.refresh_highlights()

    def refresh_highlights(self):
        with Session() as session:
            self.highlights = [
                {"term": row.term, "users": orjson.loads(row.users)} for row in session.query(Highlight).all()
            ]

    async def active_members(self, channel: discord.TextChannel) -> set:
        """
        Returns a set of all the active members in a channel.
        """
        after = datetime.datetime.now() - datetime.timedelta(minutes=config.hl.timeout)
        message_auths = set([message.author.id async for message in channel.history(after=after)])
        return message_auths

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Scan incoming messages for highlights and notify the subscribed users.
        """
        if message.author.bot:
            return

        active_members, chat = None, None
        for highlight in self.highlights:
            regex = rf"\b{re.escape(highlight['term'])}\b"
            result = re.search(regex, message.clean_content, re.IGNORECASE)

            if not result:
                continue

            if active_members is None:
                active_members = await self.active_members(message.channel)

            if chat is None:
                messages = [for_message async for for_message in message.channel.history(limit=4, before=message)]
                chat = ""
                for msg in reversed(messages):
                    chat += (
                        f"**[<t:{int(msg.created_at.timestamp())}:T>] {msg.author.name}:** {msg.clean_content[0:256]}\n"
                    )
                chat += f"✨ **[<t:{int(message.created_at.timestamp())}:T>] {message.author.name}:** \
                    {message.clean_content[0:256]}\n"

            embed = embeds.make_embed(
                title=highlight["term"],
                description=chat,
                color=discord.Color.gold(),
            )
            embed.add_field(name="Source Message", value=f"[Jump to]({message.jump_url})")

            for subscriber in highlight["users"]:
                if subscriber == message.author.id or subscriber in active_members:
                    continue

                try:
                    member = await message.guild.fetch_member(subscriber)
                except discord.errors.NotFound:
                    log.debug(f"Attempting to find member failed: {subscriber}")
                    continue

                if not message.channel.permissions_for(member).view_channel:
                    continue

                try:
                    channel = await member.create_dm()
                    await channel.send(
                        embed=embed,
                        content=(
                            f"You were mentioned with the highlight term `{highlight['term']}` "
                            f"in **{message.guild.name}** {message.channel.mention}."
                        ),
                    )
                except discord.Forbidden:
                    pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HighlightListeners(bot))
    log.info("Listener loaded: highlight")
