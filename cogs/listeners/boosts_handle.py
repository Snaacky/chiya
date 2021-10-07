import logging

import discord
from discord import Member
from discord.ext import commands

from utils import embeds
from utils.config import config

log = logging.getLogger(__name__)


class BoostsHandler(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        """
        Event Listener which is called when a Member updates their profile.

        Args:
            before (Member): The updated member’s old info.
            after (Member): The updated member’s updated info.

        Note:
            This requires Intents.members to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_member_update
        """ 
        await self.process_new_booster(before, after)
        await self.process_lost_booster(before, after)


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
        await self.on_new_boost(before, after)
        await self.on_removed_boost(before, after)


    async def on_new_boost(self, before, after):
        """ 
        Process whenever a new boost is received.

        Parameters:
            before (discord.Guild): The guild prior to being updated.
            after  (discord.Guild): The guild after being updated.
        """
        # TODO: Replace hardcoded mention with a .mention from config.
        if after.premium_subscription_count > before.premium_subscription_count:
            embed = embeds.make_embed(
                title="A new booster appeared!",
                description=(
                    "Thank you so much for the server boost! ",
                    f"We are now at {after.premium_subscription_count} boosts! ",
                    "You can contact any <@&763031634379276308> member with a ",
                    "[hex color](https://www.google.com/search?q=hex+color) "
                    "and your desired role name for a custom booster role."
                ),
                author=False, 
                color="nitro_pink",
                image_url="https://i.imgur.com/O8R98p9.gif"
            )
            await before.system_channel.send(embed=embed)

            # Attempts to create a link *near* where the boost occurred.
            nitro_logs = discord.utils.get(after.channels, id=config["channels"]["nitro_log"])
            embed = embeds.make_embed(
                description = (
                    "[A new boost was added to the server.]",
                    "(https://canary.discord.com/channels/",
                    f"{after.id}/{after.system_channel.id}/{after.system_channel.last_message_id})"
                ),
                author=False, 
                color="nitro_pink",
            )
            await nitro_logs.send(embed=embed)
            log.info(f"A new boost was added to {after.name}.")


    async def on_removed_boost(self, before, after):
        """ 
        Process whenever a new boost is removed.

        Parameters:
            before (discord.Guild): The guild prior to being updated.
            after  (discord.Guild): The guild after being updated.
        """
        if after.premium_subscription_count < before.premium_subscription_count:
            nitro_logs = discord.utils.get(after.channels, id=config["channels"]["nitro_log"])
            embed = embeds.make_embed(
                description=f"A boost was removed from the server.",
                author=False, 
                color="nitro_pink"
            )
            await nitro_logs.send(embed=embed)
            log.info(f"A boost was removed from {after.name}.")


    async def process_new_booster(self, before, after):
        """ 
        Process when a user who previously hasn't boosted the server boosts.

        Parameters:
            before (discord.Member): The updated member’s old info.
            after  (discord.Member): The updated member’s updated info.
        """
        if not before.premium_since and after.premium_since:
            channel = discord.utils.get(after.guild.channels, id=config["channels"]["nitro_log"])
            embed = embeds.make_embed(
                title="New booster",
                description=(
                    f"{after.mention} boosted the server. ",
                    f"We're now at {after.guild.premium_subscription_count} boosts."
                ),
                author=False,
                color="nitro_pink"
            )
            await channel.send(embed=embed)
            log.info(f'{after} boosted {after.guild.name}.')


    async def process_lost_booster(self, before, after):
        """ 
        Process when a user who previously boosted the server removes all of their boosts from the server.

        Parameters:
            before (discord.Member): The updated member’s old info.
            after  (discord.Member): The updated member’s updated info.
        """
        # Send an embed in #nitro-logs that someone stopped boosting the server.
        if before.premium_since and not after.premium_since:
            channel = discord.utils.get(after.guild.channels, id=config["channels"]["nitro_log"])
            embed = embeds.make_embed(
                title = "Lost booster",
                description=(
                    f"{after.mention} no longer boosts the server. ",
                    f"We're now at {after.guild.premium_subscription_count} boosts."
                ),
                author=False, 
                color="nitro_pink"
                )
            await channel.send(embed=embed)
            log.info(f'{after} stopped boosting {after.guild.name}.')


def setup(bot: commands.Bot) -> None:
    """Load the BoostsHandler cog."""
    bot.add_cog(BoostsHandler(bot))
    log.info("Listener loaded: boosts")
