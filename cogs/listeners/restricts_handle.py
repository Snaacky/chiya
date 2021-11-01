import logging

import discord
from discord import Member, Message
from discord.ext import commands

from utils import database
from utils.config import config


log = logging.getLogger(__name__)


class RestrictsHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        # Open a connection to the database.
        db = database.Database().get()

        # Get the "Restricted" role.
        role_restricted = discord.utils.get(member.guild.roles, id=config["roles"]["restricted"])

        # Check if any unfinished timed mod actions exist for the newly joined user.
        timed_restriction_entry = db["timed_mod_actions"].find_one(user_id=member.id, is_done=False)
        if timed_restriction_entry:
            await member.add_roles(role_restricted)

        # Close the connection.
        db.close()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        # Ignore bot messages.
        if message.author.bot:
            return

        # Get the guild that the member belongs to.
        guild = message.author.guild

        # Get the "Restricted" role.
        role_restricted = discord.utils.get(guild.roles, id=config["roles"]["restricted"])

        # Automatically deletes fake Discord Nitro emotes.
        if role_restricted in message.author.roles:
            if "https://cdn.discordapp.com/emojis/" in message.content:
                await message.delete()


def setup(bot) -> None:
    """Load the cog."""
    bot.add_cog(RestrictsHandler(bot))
    log.info("Listener Loaded: restricts")
