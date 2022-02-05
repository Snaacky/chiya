import logging

import discord
from discord.ext import commands

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class BoostListener(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        await self.on_new_booster(before, after)
        await self.on_lost_booster(before, after)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        await self.on_new_boost(before, after)

    async def on_new_boost(self, before: discord.Guild, after: discord.Guild) -> None:
        """
        Send a notification embed when a new boost was received.
        """
        if after.premium_subscription_count > before.premium_subscription_count:
            embed = embeds.make_embed(
                color=discord.Color.nitro_pink(),
                image_url="https://i.imgur.com/O8R98p9.gif",
                title="A new booster appeared!",
                description=(
                    "Thank you so much for the server boost! "
                    f"We are now at {after.premium_subscription_count} boosts! "
                    f"You can contact any <@&{config['roles']['staff']}> member with a "
                    "[hex color](https://www.google.com/search?q=hex+color) "
                    "and your desired role name for a custom booster role."
                ),
            )
            await before.system_channel.send(embed=embed)

    async def on_new_booster(self, before: discord.Member, after: discord.Member) -> None:
        """
        Send an embed in #nitro-logs when a new boost was received.
        """
        if not before.premium_since and after.premium_since:
            channel = discord.utils.get(after.guild.channels, id=config["channels"]["nitro_log"])
            embed = embeds.make_embed(
                color=discord.Color.nitro_pink(),
                title="New booster",
                description=(
                    f"{after.mention} boosted the server. "
                    f"We're now at {after.guild.premium_subscription_count} boosts."
                ),
            )
            await channel.send(embed=embed)
            log.info(f"{after} boosted {after.guild.name}.")

    async def on_lost_booster(self, before: discord.Member, after: discord.Member) -> None:
        """
        Send an embed in #nitro-logs when a boost was lost.
        """
        if before.premium_since and not after.premium_since:
            channel = discord.utils.get(after.guild.channels, id=config["channels"]["nitro_log"])
            embed = embeds.make_embed(
                color=discord.Color.nitro_pink(),
                title="Lost booster",
                description=(
                    f"{after.mention} no longer boosts the server. "
                    f"We're now at {after.guild.premium_subscription_count} boosts."
                ),
            )
            await channel.send(embed=embed)
            log.info(f"{after} stopped boosting {after.guild.name}.")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(BoostListener(bot))
    log.info("Listener loaded: boost")
