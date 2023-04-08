import logging
import time

import discord
from discord.ext import commands

from chiya import database


log = logging.getLogger(__name__)


class MuteListener(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        """
        Add the user's mute entry to the database if they were timed out manually.
        """
        if not before.timed_out_until and after.timed_out_until:
            logs = [log async for log in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update)]
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
        
        if not after.timed_out_until and before.timed_out_until:
            logs = [log async for log in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update)]
            if logs[0].user != self.bot.user:
                db = database.Database().get()
                db["mod_logs"].insert(
                    dict(
                        user_id=after.id,
                        mod_id=logs[0].user.id,
                        timestamp=int(time.time()),
                        reason=logs[0].reason,
                        type="unmute",
                    )
                )
                db.commit()
                db.close()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MuteListener(bot))
    log.info("Listener loaded: mute")
