import logging

import discord
from discord import Member, Message
from discord.ext import commands

from utils import database
from utils.config import config


log = logging.getLogger(__name__)


class RestrictListener(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        db = database.Database().get()
        result = db["timed_mod_actions"].find_one(user_id=member.id, is_done=False)
        if result:
            await member.add_roles(discord.utils.get(member.guild.roles, id=config["roles"]["restricted"]))
        db.close()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return

        if discord.utils.get(message.guild.roles, id=config["roles"]["restricted"]) in message.author.roles:
            if "https://cdn.discordapp.com/emojis/" in message.content:
                await message.delete()


def setup(bot) -> None:
    bot.add_cog(RestrictListener(bot))
    log.info("Listener Loaded: restrict")
