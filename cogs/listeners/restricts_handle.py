import logging

import dataset
import discord
from discord import Member
from discord.ext import commands

import config
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

        guild = member.guild

        role = discord.utils.get(guild.roles, id=config.role_restricted)

        timed_restriction_entry = db["timed_mod_actions"].find_one(user_id=member.id, is_done=False)
        if timed_restriction_entry and timed_restriction_entry["user_id"] == member.id:
            await member.add_roles(role)

        # Close the connection.
        db.close()


def setup(bot) -> None:
    """Load the cog."""
    bot.add_cog(RestrictsHandler(bot))
    log.info("Listener Loaded: restricts")
