import logging
import time

import discord
from discord import Member
from discord.ext import commands

from utils import database, embeds
from utils.config import config


log = logging.getLogger(__name__)


class MuteListener(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        channel = discord.utils.get(member.guild.channels, name=f"mute-{member.id}")
        if not channel:
            return

        user = await self.bot.fetch_user(member.id)
        db = database.Database().get()

        results = db["mod_logs"].find_one(user_id=member.id, type="mute")
        if results:
            db["mod_logs"].insert(dict(
                user_id=user.id,
                mod_id=self.bot.user.id,
                timestamp=int(time.time()),
                reason="Mute evasion.",
                type="unmute"
            ))

        results = db["timed_mod_actions"].find_one(user_id=member.id, is_done=False, action_type="mute")
        if results:
            db["timed_mod_actions"].update(dict(id=results["id"], is_done=True), ["id"])

        mutes = self.bot.get_cog("MuteCommands")
        await mutes.archive_mute_channel(
            ctx=None,
            user_id=user.id,
            reason="Mute channel archived after member banned due to mute evasion."
        )

        db["mod_logs"].insert(dict(
            user_id=user.id,
            mod_id=self.bot.user.id,
            timestamp=int(time.time()),
            reason="Mute evasion.",
            type="ban"
        ))
        await member.guild.ban(user, reason="Mute evasion.")

        embed = embeds.make_embed(
            ctx=None,
            title=f"Member {user.name}#{user.discriminator} banned",
            description=f"{user.mention} was banned indefinitely because they evaded their timed mute by leaving.",
            thumbnail_url="https://i.imgur.com/l0jyxkz.png",
            color="soft_red"
        )
        channel = member.guild.get_channel(config["channels"]["moderation"])
        await channel.send(embed=embed)
        db.commit()
        db.close()


def setup(bot) -> None:
    """Load the cog."""
    bot.add_cog(MuteListener(bot))
    log.info("Listener Loaded: mute")
