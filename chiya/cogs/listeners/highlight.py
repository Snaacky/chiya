import datetime
import logging
import re

import discord
import orjson
from discord.ext import commands

from chiya import config, database
from chiya.utils import embeds


log = logging.getLogger(__name__)


class HighlightListeners(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db = database.Database().get()
        self.highlights = [
            {
                "term": highlight["term"],
                "users": orjson.loads(highlight["users"])
            }
            for highlight in self.db["highlights"].find()
        ]

    def refresh_highlights(self):
        self.highlights = [
            {
                "term": highlight["term"],
                "users": orjson.loads(highlight["users"])
            }
            for highlight in self.db["highlights"].find()
        ]

    async def is_user_active(self, channel: discord.TextChannel, member: discord.Member) -> bool:
        """
        Checks if the user was active in chat recently.
        """
        after = datetime.datetime.now() - datetime.timedelta(minutes=config["hl"]["timeout"])
        message_auths = [message.author.id async for message in channel.history(after=after)]
        return member.id in message_auths

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Scan incoming messages for highlights and notify the subscribed users.
        """
        if message.author.bot:
            return

        for highlight in self.highlights:
            regex = rf"\b{re.escape(highlight['term'])}\b"
            result = re.search(regex, message.clean_content, re.IGNORECASE)

            if not result:
                continue

            messages = [for_message async for for_message in message.channel.history(limit=4, before=message)]
            chat = ""
            for msg in reversed(messages):
                chat += f"**[<t:{int(msg.created_at.timestamp())}:T>] {msg.author.name}:** {msg.clean_content[0:256]}\n"
            chat += f"✨ **[<t:{int(message.created_at.timestamp())}:T>] {message.author.name}:** \
                {message.clean_content[0:256]}\n"

            embed = embeds.make_embed(
                title=highlight["term"],
                description=chat,
                color=discord.Color.gold(),
            )
            embed.add_field(name="Source Message", value=f"[Jump to]({message.jump_url})")

            for subscriber in highlight["users"]:
                try:
                    member = await message.guild.fetch_member(subscriber)
                except discord.errors.NotFound:
                    log.debug("Attempting to find member failed: " + subscriber)
                    continue

                if (
                    subscriber == message.author.id
                    or not message.channel.permissions_for(member).view_channel
                    or await self.is_user_active(message.channel, member)
                ):
                    continue

                try:
                    channel = await member.create_dm()
                    await channel.send(
                        embed=embed,
                        content=(
                            f"You were mentioned with the highlight term `{highlight['term']}` "
                            f"in **{message.guild.name}** {message.channel.mention}."
                        )
                    )
                except discord.Forbidden:
                    pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HighlightListeners(bot))
    log.info("Listener loaded: highlight")
