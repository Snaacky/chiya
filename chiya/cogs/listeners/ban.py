import logging
import time
from typing import Union

import discord
from discord.ext import commands

from chiya import database


log = logging.getLogger(__name__)


class BanListeners(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.Member | discord.User) -> None:
        """
        Add the user's ban entry to the database if they were banned manually.
        """
        ban_entry = await guild.fetch_ban(user)
        logs = await guild.audit_logs(limit=1, action=discord.AuditLogAction.ban).flatten()
        if logs[0].user != self.bot.user:
            db = database.Database().get()
            db["mod_logs"].insert(
                dict(
                    user_id=user.id,
                    mod_id=logs[0].user.id,
                    timestamp=int(time.time()),
                    reason=ban_entry.reason,
                    type="ban",
                )
            )
            db.commit()
            db.close()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(BanListeners(bot))
    log.info("Listeners loaded: ban")
