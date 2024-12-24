import discord
from discord.ext import commands
from loguru import logger

from chiya.config import config
from chiya.utils import embeds


class BoostCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Send a notification embed when a new boost was received.
        """
        if not message.type == discord.MessageType.premium_guild_subscription:
            return

        member = message.author
        guild = message.guild

        logger.info(f"{member} boosted {guild.name}")

        embed = embeds.make_embed(
            color=discord.Color(0xF47FFF),
            image_url="https://i.imgur.com/O8R98p9.gif",
            title="A new booster appeared!",
            description=(
                f"{member.mention}, thank you so much for the server boost! "
                f"We are now at {guild.premium_subscription_count} boosts! "
                f"You can create a new ticket in <#{config.channels.tickets}> "
                "with your desired role name, icon (must be transparent), "
                "and [hex color](https://www.google.com/search?q=hex+color) for a custom booster role."
            ),
        )

        message = await message.channel.send(embed=embed)
        embed = embeds.make_embed(
            color=discord.Color(0xF47FFF),
            title="New booster",
            description=(
                f"{member.mention} [boosted]({message.jump_url}) the server. "
                f"We're now at {guild.premium_subscription_count} boosts."
            ),
        )

        channel = discord.utils.get(guild.channels, id=config.channels.nitro_log)
        await channel.send(content=member.mention, embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """
        Send an embed in #nitro-logs when a boost was lost.
        """
        # TODO: Invert this logic so we can return early and remove some indenting
        if before.premium_since and not after.premium_since:
            channel = discord.utils.get(after.guild.channels, id=config.channels.nitro_log)
            embed = embeds.make_embed(
                color=discord.Color(0xF47FFF),
                title="Lost booster",
                description=(
                    f"{after.mention} no longer boosts the server. "
                    f"We're now at {after.guild.premium_subscription_count} boosts."
                ),
            )
            await channel.send(content=after.mention, embed=embed)
            logger.info(f"{after} stopped boosting {after.guild.name}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BoostCog(bot))
