import logging
import time

import discord
from chiya import database
from discord.ext import commands

log = logging.getLogger(__name__)


class MuteListeners(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        """
        Add the user's mute entry to the database if they were timed out manually.
        """
        if after.timed_out:
            logs = await after.guild.audit_logs(
                limit=1, action=discord.AuditLogAction.member_update
            ).flatten()
            if logs[0].user != self.bot.user:
                db = database.Database().get()
                db["mod_logs"].insert(
                    dict(
                        user_id=after.id,
                        mod_id=logs[0].user.id,
                        timestamp=int(time.time()),
                        reason=logs[0].reason,
                        type="mute",
                    )
                )
                db.commit()
                db.close()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(MuteListeners(bot))
    log.info("Listeners loaded: mute")
