import logging
import time

import dataset
import discord
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
        """Event Listener which is called when a Member leaves a Guild.

        Args:
            member (Member): The member who left.

        Note:
            This requires Intents.members to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_member_remove
        """
        with dataset.connect(database.get_db()) as db:
            action = db['timed_mod_actions'].find_one(user_id=member.id, is_done=False, action_type='mute')
            guild = member.guild

            if action:
                user = await self.bot.fetch_user(member.id)
                # Creating the embed used to alert the moderators that the mute evading member was banned.
                embed = embeds.make_embed(
                    ctx=None,
                    title=f"Member {user.name}#{user.discriminator} banned.",
                    description=f"User {user.mention} was banned indefinitely because they evaded their timed mute by leaving.",
                    thumbnail_url=config.user_ban,
                    color="soft_red"
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
                await mutes.archive_mute_channel(
                    user_id=user.id,
                    guild=guild,
                    unmute_reason="Mute channel archived after member banned due to mute evasion."
                )
                await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        """Event Listener which is called when a Member updates their profile.

        Args:
            before (Member): The updated member’s old info.
            after (Member): The updated member’s updated info.

        Note:
            This requires Intents.members to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_member_update
        """

        # If the mute role is manually removed from a user, re-add it automatically.
        # Only do this operation on role count changes to try avoiding hitting Discord API unnecessarily.
        if len(before.roles) != len(after.roles):
            mute_role = discord.utils.get(before.guild.roles, id=config.role_muted)
            if mute_role in before.roles and mute_role not in after.roles:
                mute_cog = self.bot.get_cog("MuteCog")
                if await mute_cog.is_user_muted(guild=before.guild, member=before):
                    await before.add_roles(mute_role)

def setup(bot) -> None:
    """Load the cog."""
    bot.add_cog(MutesHandler(bot))
    log.info("Listener Loaded: mutes")
