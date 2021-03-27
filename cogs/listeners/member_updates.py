import logging
from typing import Union

import discord
from discord import User, Member, Guild
from discord.ext import commands

from utils import embeds

log = logging.getLogger(__name__)


class MemberUpdates(commands.Cog):
    """Member event handler cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild: Guild, user: Union[User, Member]) -> None:
        """Event Listener which is called when a user gets banned from a Guild.

        Args:
            guild (Guild): The guild the user got banned from.
            user (Union[User, Member]): he user that got banned.
                Can be either User or Member depending if the user was in the guild or not at the time of removal.

        Note:
            This requires Intents.bans to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_member_ban
        """
        log.info(f'{user.name}-{user.id} was banned from {guild.name}')

    @commands.Cog.listener()
    async def on_member_unban(self, guild: Guild, user: User) -> None:
        """Event Listener which is called when a user gets unbanned from a Guild.

        Args:
            guild (Guild): The guild the user got unbanned from.
            user (User): The user that got unbanned.
        
        Note:
            This requires Intents.bans to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_member_unban
        """
        log.info(f'{user.name}-{user.id} was unbanned from {guild.name}')

    @commands.Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        """Event Listener which is called when a Member joins a Guild.

        Args:
            member (Member): The member who joined.

        Note:
            This requires Intents.members to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_member_join
        """
        log.info(f'{member} has joined {member.guild.name}.')

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
        log.info(f'{member} has left {member.guild.name}.')

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
        # Psuedo on_nitro_boost event
        if before.premium_since is None and after.premium_since is not None:
            guild = before.guild
            embed = embeds.make_embed(author=False, color=0xff73fa)
            embed.title = f"{before.name} boosted the server"
            embed.description = f"""Thank you so much for the server boost! We are now at {guild.premium_subscription_count} boosts!

            You can contact any <@&763031634379276308> member with a [hex color](https://www.google.com/search?q=hex+color) and your desired role name for a custom booster role."""
            embed.set_image(url="https://i.imgur.com/O8R98p9.gif")
            await guild.system_channel.send(embed=embed)


def setup(bot: commands.Bot) -> None:
    """Load the member_updates cog."""
    bot.add_cog(MemberUpdates(bot))
    log.info("Cog loaded: member_updates")
