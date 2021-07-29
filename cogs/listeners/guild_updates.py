import logging
import datetime

import discord
from discord.ext import commands

from handlers import boosts
from utils import embeds

log = logging.getLogger(__name__)

class GuildUpdates(commands.Cog):
    """Guild event handler cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild) -> None:
        """Event Listener which is called when a guild becomes available.

        Args:
            guild (discord.Guild): The Guild that has become available.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_available
        """
        log.info(f'{guild.name} has become available.')

    @commands.Cog.listener()
    async def on_guild_unavailable(self, guild: discord.Guild) -> None:
        """Event Listener which is called when a guild becomes unavailable.

        Args:
            guild (discord.Guild): The Guild that has become unavailable.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_unavailable
        """
        log.info(f'{guild.name} is now unavailable.')

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        """Event Listener which is called whenever a guild channel is created.

        Args:
            channel (discord.abc.GuildChannel): The guild channel that was created.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_channel_create
        """
        log.info(f'{channel.name} has been created in {channel.guild}.')

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        """Event Listener which is called whenever a guild channel is deleted.

        Args:
            channel (discord.abc.GuildChannel): The guild channel that was deleted.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_channel_delete
        """
        log.info(f'{channel.name} has been deleted in {channel.guild}.')

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel: discord.abc.GuildChannel, last_pin: datetime.datetime) -> None:
        """Event Listener which is called whenever a message is pinned or unpinned from a guild channel.

        Args:
            channel (discord.abc.GuildChannel): The guild channel that had its pins updated.
            last_pin (datetime.datetime): The latest message that was pinned as a naive datetime in UTC. Could be None.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_channel_pins_update
        """
        log.info(f'{channel.name} updated its pin: {last_pin}.')

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
        """Event Listener which is called whenever a guild channel is updated. e.g. changed name, topic, permissions.

        Args:
            before (discord.abc.GuildChannel): The updated guild channel’s old info.
            after (discord.abc.GuildChannel): The updated guild channel’s new info.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_channel_update
        """

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: discord.Emoji, after: discord.Emoji) -> None:
        """Event Listener which is called when a Guild adds or removes Emoji.

        Args:
            guild (discord.Guild): The guild who got their emojis updated.
            before (discord.Emoji): A list of emojis before the update.
            after (discord.Emoji): A list of emojis after the update.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_emojis_update
        """

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild: discord.Guild) -> None:
        """Event Listener which is called whenever an integration is created, modified, or removed from a guild.

        Args:
            guild (discord.Guild): The guild that had its integrations updated.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_integrations_update
        """

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Event Listener which is called when a Guild is either created by the Bot or when the Bot joins a guild.

        Args:
            guild (discord.Guild): The guild that was joined.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_join
        """
        log.info(f'{guild.name} has a joined a new guild')

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Event Listener which is called when a Guild is removed from the Client.

        Args:
            guild (discord.Guild): The guild that got removed.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_remove
        """

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        """Event Listener which is called when a Guild creates a new Role.

        Args:
            role (discord.Role): The role that was created.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_role_create
        """

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        """Event Listener which is called when a Guild deletes a Role.

        Args:
            role (discord.Role): The role that was deleted.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_role_delete
        """

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        """Event Listener which is called when a Role is changed guild-wide.

        Args:
            before (discord.Role): The updated role’s old info.
            after (discord.Role): The updated role’s updated info.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_role_update
        """

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        """Event Listener which is called when a Guild updates.

        Args:
            before (discord.Guild): The guild prior to being updated.
            after (discord.Guild): The guild after being updated.

        Note:
            This requires Intents.guilds to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_update
        """
        await boosts.on_new_boost(before, after)
        await boosts.on_removed_boost(before, after)

def setup(bot: commands.Bot) -> None:
    """Load the guild_updates cog."""
    bot.add_cog(GuildUpdates(bot))
    log.info("Listener loaded: guild_updates")
