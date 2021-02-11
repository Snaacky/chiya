import logging
import datetime
from os import name

import discord
from discord.enums import AuditLogAction, AuditLogActionCategory
from discord.ext import commands


import constants
from utils import embeds
from utils import utils


log = logging.getLogger(__name__)

class GuildUpdates(commands.Cog):
    """Guild event handler cog."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        guild = self.bot.get_guild(constants.Guild.id)
    

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
        log.info(f'{guild.name} has has become available.')

    @commands.Cog.listener()
    async def on_guild_unavailable(self, guild: discord.Guild) -> None:
        """Event Listener which is called when a guild becomes unavailable.

        Args:
            guild (discord.Guild): The Guild that has become unavailable.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_guild_unavailable
        """
        log.info(f'{guild.name} has has become unavailable.')

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
        
        log_channel = await self.bot.fetch_channel(constants.Guild.channels['chiya_logs'])
        guild = await self.bot.fetch_guild(constants.Guild.id)
        audit_log_entry = None
        async for x in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            audit_log_entry = x
            break
        
        await log_channel.send(f"`CREATED:` Channel `#{channel.name}`({channel.id}) was created at `{utils.time_now()}` by `{audit_log_entry.user.name}#{audit_log_entry.user.discriminator}`({audit_log_entry.user.id}).")
        
        log.info(f'{channel.name} has has been created in {channel.guild}.')

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
        
        # TODO Make log_channel, guild global variables to reduce redundancy
        log_channel = await self.bot.fetch_channel(constants.Guild.channels['chiya_logs'])
        audit_log_entry = None
        guild = await self.bot.fetch_guild(constants.Guild.id)
        async for x in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            audit_log_entry = x
            break
        
        await log_channel.send(f"`DELETED:` Channel `#{channel.name}`({channel.id}) was deleted at `{utils.time_now()}` by `{audit_log_entry.user.name}#{audit_log_entry.user.discriminator}`({audit_log_entry.user.id}).")
        
        log.info(f'{channel.name} has has been deleted in {channel.guild}.')

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
        
        
        log_channel = await self.bot.fetch_channel(constants.Guild.channels['chiya_logs'])
        await log_channel.send(f"A message was pinned/unpinned in `#{channel.name}`({channel.mention}) at `{utils.time_now()}`.")

        log.info(f'Message pinned in `{channel.name}` at `{last_pin}`.')



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
        
        log_channel = await self.bot.fetch_channel(constants.Guild.channels['chiya_logs'])
        
        audit_log_entry = None
        guild = await self.bot.fetch_guild(constants.Guild.id)
        
        async for x in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
            audit_log_entry = x
            break

        changes = audit_log_entry.changes
        
        message = "`UPDATED:`\n"
        
        for key, value in iter(changes.before):
            message += f"`BEFORE:` {key} : {value}\n"
            for key, value in iter(changes.after):
                message += f"`AFTER:` {key} : {value}\n"
            break

        message += f"`TIME:` `{utils.time_now()}`\n"
        message += f"`USER:` `{audit_log_entry.user.name}#{audit_log_entry.user.discriminator}`({audit_log_entry.user.id})"
        await log_channel.send(message)
        

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
        
        log_channel = await self.bot.fetch_channel(constants.Guild.channels['chiya_logs'])
        
        audit_log_entry = None
        guild = await self.bot.fetch_guild(constants.Guild.id)
        
        async for x in guild.audit_logs(limit=1):
            audit_log_entry = x
            break

        changes = audit_log_entry.changes
        
        message = "`UPDATED:`\n"
        
        for key, value in iter(changes.before):
            message += f"`BEFORE:` {key} : {value}\n"
            for key, value in iter(changes.after):
                message += f"`AFTER:` {key} : {value}\n"
            break

        message += f"`TIME:` `{utils.time_now()}`\n"
        message += f"`USER:` `{audit_log_entry.user.name}#{audit_log_entry.user.discriminator}`({audit_log_entry.user.id})"
        
        await log_channel.send(message)

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
        
        log_channel = await self.bot.fetch_channel(constants.Guild.channels['chiya_logs'])
        await log_channel.send(f"`CREATED:` Role `@{role.name}`({role.mention}) was created at `{utils.time_now()}`.")

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
        
        log_channel = await self.bot.fetch_channel(constants.Guild.channels['chiya_logs'])
        await log_channel.send(f"`DELETED:` Role `@{role.name}` was deleted at `{utils.time_now()}`.")

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
        
        
        log_channel = await self.bot.fetch_channel(constants.Guild.channels['chiya_logs'])
        
        audit_log_entry = None
        guild = await self.bot.fetch_guild(constants.Guild.id)
        
        async for x in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
            audit_log_entry = x
            break

        changes = audit_log_entry.changes
        
        message = "`UPDATED:`\n"
        
        for key, value in iter(changes.before):
            message += f"`BEFORE:` {key} : {value}\n"
            for key, value in iter(changes.after):
                message += f"`AFTER:` {key} : {value}\n"
            break

        message += f"`TIME:` `{utils.time_now()}`\n"
        message += f"`USER:` `{audit_log_entry.user.name}#{audit_log_entry.user.discriminator}`({audit_log_entry.user.id})"
        await log_channel.send(message)

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
        
        
        log_channel = await self.bot.fetch_channel(constants.Guild.channels['chiya_logs'])
        await log_channel.send(f"`UPDATED:` Guild was updated at `{utils.time_now}`.")

def setup(bot: commands.Bot) -> None:
    """Load the guild_updates cog."""
    bot.add_cog(GuildUpdates(bot))
    log.info("Cog loaded: guild_updates")
