import logging
import time

import dataset
from discord import Member
from discord.ext import commands

import config
from utils import database, embeds

# Enabling logs
log = logging.getLogger(__name__)


class MutesHandler(commands.Cog):
    """Handles actions such as mute evasion."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        with dataset.connect(database.get_db()) as db:
            action = db['timed_mod_actions'].find_one(user_id=member.id, is_done=False, action_type='mute')
            guild = member.guild

            if action:
                user = await self.bot.fetch_user(member.id)
                # Creating the embed used to alert the moderators that the mute evading member was banned.
                embed = embeds.make_embed(ctx=None,
                                          title=f"Member {user.name}#{user.discriminator} banned.",
                                          description=f"User {user.mention} was permanently banned because they evaded their timed mute by leaving."
                                          )

                channel = guild.get_channel(config.mod_channel)
                await guild.ban(user, reason="Mute Evasion.")

                # Add the ban to the mod_log database.
                db["mod_logs"].insert(dict(
                    user_id=user.id,
                    mod_id=self.bot.user.id,
                    timestamp=int(time.time()),
                    reason="Mute Evasion.",
                    type="ban"
                ))
                # Resolving the mute so that we don't have to deal with it separately.
                db["timed_mod_actions"].update(dict(id=action["id"], is_done=True), ["id"])

                # Archive the mute channel
                mutes = self.bot.get_cog("MuteCog")
                await mutes.archive_mute_channel(user_id=user.id,
                                                 guild=guild,
                                                 unmute_reason="Mute channel archived after member banned due to mute evasion."
                                                 )
                await channel.send(embed=embed)


def setup(bot) -> None:
    """Load the cog."""
    bot.add_cog(MutesHandler(bot))
    log.info("Listener Loaded: mutes")
