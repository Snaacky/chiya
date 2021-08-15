import logging

import dataset
import discord
from discord import Member, Message
from discord.ext import commands

from cogs.commands import settings
from utils import database

# Enabling logs
log = logging.getLogger(__name__)


class RestrictsHandler(commands.Cog):
    """Handles restrict evasion."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        # Get the guild that the member belongs to.
        guild = member.guild

        # Get the "Restricted" role.
        role_restricted = discord.utils.get(guild.roles, id=settings.get_value("role_restricted"))

        # Get the restrict entries with is_done = False from database and check if its ID matches the user who just joined.
        timed_restriction_entry = db["timed_mod_actions"].find_one(user_id=member.id, is_done=False)
        if timed_restriction_entry and timed_restriction_entry["user_id"] == member.id:
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
        role_restricted = discord.utils.get(guild.roles, id=settings.get_value("role_restricted"))

        # Automatically deletes fake Discord Nitro emotes.
        if role_restricted in message.author.roles:
            if "https://cdn.discordapp.com/emojis/" in message.content:
                await message.delete()


def setup(bot) -> None:
    """Load the cog."""
    bot.add_cog(RestrictsHandler(bot))
    log.info("Listener Loaded: restricts")
