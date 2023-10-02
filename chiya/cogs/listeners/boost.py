import logging

import discord
from discord.ext import commands

from chiya import config
from chiya.utils import embeds, lfs


log = logging.getLogger(__name__)


class BoostListeners(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        await self.on_lost_booster(before, after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.type == discord.MessageType.premium_guild_subscription:
            await self.on_new_boost(message)

    NITRO_PINK = discord.Color(0xf47fff)

    async def on_new_boost(self, message: discord.Message) -> None:
        """
        Send a notification embed when a new boost was received.
        """
        member = message.author
        guild = message.guild

        embed = embeds.make_embed(
            color=self.NITRO_PINK,
            image_url=lfs.get_image("new-boost.gif"),
            title="A new booster appeared!",
            description=(
                f"{member.mention}, thank you so much for the server boost! "
                f"We are now at {guild.premium_subscription_count} boosts! "
                f"You can create a new ticket in <#{config['channels']['server']['tickets']}> "
                "with your desired role name, icon (must be transparent), "
                "and [hex color](https://www.google.com/search?q=hex+color) for a custom booster role."
            ),
        )
        boost_message = await message.channel.send(embed=embed)

        channel = discord.utils.get(guild.channels, id=config["channels"]["logs"]["nitro_log"])
        embed = embeds.make_embed(
            color=self.NITRO_PINK,
            title="New booster",
            description=(
                f"{member.mention} [boosted]({boost_message.jump_url}) the server. "
                f"We're now at {guild.premium_subscription_count} boosts."
            ),
        )
        await channel.send(embed=embed)
        log.info(f"{member} boosted {guild.name}")

    async def on_lost_booster(self, before: discord.Member, after: discord.Member) -> None:
        """
        Send an embed in #nitro-logs when a boost was lost.
        """
        if before.premium_since and not after.premium_since:
            channel = discord.utils.get(after.guild.channels, id=config["channels"]["logs"]["nitro_log"])
            embed = embeds.make_embed(
                color=self.NITRO_PINK,
                title="Lost booster",
                description=(
                    f"{after.mention} no longer boosts the server. "
                    f"We're now at {after.guild.premium_subscription_count} boosts."
                ),
            )
            await channel.send(embed=embed)
            log.info(f"{after} stopped boosting {after.guild.name}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BoostListeners(bot))
    log.info("Listeners loaded: boost")
