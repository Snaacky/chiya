import logging
import time

import dataset
import discord
from discord import Member
from discord.ext import commands

from cogs.commands import settings
from utils import database, embeds

# Enabling logs
log = logging.getLogger(__name__)


class MutesHandler(commands.Cog):
    """Handles actions such as mute evasion."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        guild = member.guild
        mute_channel = discord.utils.get(guild.channels, name=f"mute-{member.id}")

        if mute_channel:
            mod_channel = guild.get_channel(settings.get_value("channel_moderation"))
            user = await self.bot.fetch_user(member.id)

            # Add an unmute entry in the database to prevent archive_mute_channel()'s unmuter throwing NoneType() exception.
            mute_entry = db["mod_logs"].find_one(user_id=member.id, type="mute")
            # Add an "unmute" entry into the database.
            if mute_entry:
                db["mod_logs"].insert(dict(
                    user_id=user.id,
                    mod_id=self.bot.user.id,
                    timestamp=int(time.time()),
                    reason="Mute evasion.",
                    type="unmute"
                ))

            # Update the mute entry in the timed_mod_actions database to prevent issues with task looping.
            tempmute_entry = db["timed_mod_actions"].find_one(user_id=member.id, is_done=False, action_type="mute")
            if tempmute_entry:
                db["timed_mod_actions"].update(dict(id=tempmute_entry["id"], is_done=True), ["id"])

            # Archive the mute channel
            mutes = self.bot.get_cog("MuteCog")
            await mutes.archive_mute_channel(
                ctx=None,
                user_id=user.id,
                reason="Mute channel archived after member banned due to mute evasion.",
                guild=guild,
            )

            # Add the ban to the mod_log database.
            db["mod_logs"].insert(dict(
                user_id=user.id,
                mod_id=self.bot.user.id,
                timestamp=int(time.time()),
                reason="Mute evasion.",
                type="ban"
            ))

            # Ban the user.
            await guild.ban(user, reason="Mute evasion.")

            # Creating the embed used to alert the moderators that the mute evading member was banned.
            embed = embeds.make_embed(
                ctx=None,
                title=f"Member {user.name}#{user.discriminator} banned",
                description=f"User {user.mention} was banned indefinitely because they evaded their timed mute by leaving.",
                thumbnail_url="https://i.imgur.com/l0jyxkz.png",
                color="soft_red"
            )
            await mod_channel.send(embed=embed)

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()


def setup(bot) -> None:
    """Load the cog."""
    bot.add_cog(MutesHandler(bot))
    log.info("Listener Loaded: mutes")
