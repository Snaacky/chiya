import logging
import time
from typing import Union

import discord
from discord import User, Member, Guild
from discord.ext import commands

from utils import database


log = logging.getLogger(__name__)


class BansHandler(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild: Guild, user: Union[User, Member]):
        # Open a connection to the database.
        db = database.Database().get()

        # Get the ban entry of the user who just got banned.
        ban_entry = await guild.fetch_ban(user)

        """
        Attempts to get the ban author from the most recent ban entry from the mod log. We can use
        "async for entry in logs:" to convert the AsyncIterator into a list but it's not as clean as flatten().
        See: https://discordpy.readthedocs.io/en/stable/api.html?highlight=audit_logs#discord.Guild.audit_logs
        """
        logs = await guild.audit_logs(limit=1, action=discord.AuditLogAction.ban).flatten()

        # Get the most recent ban entry in the audit log.
        logs = logs[0]

        # If the ban author was not a bot (manual ban), add the entry into the database.
        if logs.user != self.bot.user:
            db["mod_logs"].insert(dict(
                user_id=user.id,
                mod_id=logs.user.id,
                timestamp=int(time.time()),
                reason=ban_entry.reason,
                type="ban"
            ))

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()


def setup(bot: commands.Bot) -> None:
    """Load the BansHandler cog."""
    bot.add_cog(BansHandler(bot))
    log.info("Listener loaded: bans")
