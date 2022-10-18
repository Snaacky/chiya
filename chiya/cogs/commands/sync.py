import logging

import discord
from discord import app_commands
from discord.ext import commands

from chiya import config
from chiya.utils import embeds

log = logging.getLogger(__name__)


class SyncCog(commands.GroupCog, group_name="admin"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    sync = app_commands.Group(name="sync", description="Sync commands")

    @sync.command(name="global", description="Sync commands globally.")
    @app_commands.checks.has_role(config["roles"]["staff"])
    async def sync_global(self, interaction: discord.Interaction) -> None:
        """
        Does not sync all commands globally, just the ones registered as global.
        """
        await interaction.response.defer()
        synced = await self.bot.tree.sync()
        await embeds.success_message(ctx=interaction, description=f"Synced {len(synced)} commands globally.")

    @sync.command(name="guild", description="Sync commands in the current guild")
    @app_commands.checks.has_role(config["roles"]["staff"])
    async def sync_guild(self, interaction: discord.Interaction) -> None:
        """
        Does not sync all of your commands to that guild, just the ones registered to that guild.
        """
        await interaction.response.defer()
        synced = await self.bot.tree.sync(guild=interaction.guild)
        await embeds.success_message(ctx=interaction, description=f"Synced {len(synced)} commands to the current guild.")

    @sync.command(name="copy", description="Copies all global app commands to current guild and syncs")
    @app_commands.checks.has_role(config["roles"]["staff"])
    async def sync_global_to_guild(self, interaction: discord.Interaction) -> None:
        """
        This will copy the global list of commands in the tree into the list of commands for the specified guild.
        This is not permanent between bot restarts, and it doesn't impact the state of the commands (you still have to sync).
        """
        await interaction.response.defer()
        self.bot.tree.copy_global_to(guild=interaction.guild)
        synced = await self.bot.tree.sync(guild=interaction.guild)
        await embeds.success_message(ctx=interaction, description=f"Copied and synced {len(synced)} global app commands to the current guild.")

    @sync.command(name="remove", description="Clears all commands from the current guild target and syncs")
    @app_commands.checks.has_role(config["roles"]["staff"])
    async def sync_remove(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.bot.tree.clear_commands(guild=interaction.guild)
        await self.bot.tree.sync(guild=interaction.guild)
        await embeds.success_message(ctx=interaction, description="Cleared all commands from the current guild and synced.")

    @sync_global.error
    @sync_guild.error
    @sync_global_to_guild.error
    @sync_remove.error
    async def sync_error(self, interaction: discord.Interaction, error: discord.HTTPException) -> None:
        await interaction.response.defer()

        if isinstance(error, discord.app_commands.errors.MissingRole):
            embed = embeds.error_embed(ctx=interaction, description=f"Role <@&{error.missing_role}> is required to use this command.")
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SyncCog(bot))
    log.info("Commands loaded: sync")
