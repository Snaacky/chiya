import logging

import dataset
import discord
from discord import Member
from discord.ext import commands

import config
from utils import database

# Enabling logs
log = logging.getLogger(__name__)


class MutesHandler(commands.Cog):
    """Handles actions such as mute evasion."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        with dataset.connect(database.get_db()) as db:
            result = db['timed_mod_actions'].find_one(user_id=member.id, is_done=False, action_type='mute')
            guild = member.guild

            # Adds "Muted" role to member.
            if result:
                role = discord.utils.get(guild.roles, id=config.role_muted)
                await member.add_roles(role, reason="Re-muted evading member who was previously muted.")
                
                channel = guild.get_channel(result['channel_id'])
                if channel:
                    await channel.send(f"{member.mention} was re-muted after evading a timed mute.")

def setup(bot) -> None:
    """Load the cog."""
    bot.add_cog(MutesHandler(bot))
    log.info("Cog loaded: MutesHandler.")