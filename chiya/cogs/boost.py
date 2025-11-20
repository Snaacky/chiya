import discord
from discord.ext import commands
from loguru import logger

from chiya.config import config


class BoostCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Send a notification embed when a new boost was received.
        """
        if not message.guild or not message.type == discord.MessageType.premium_guild_subscription:
            return

        logger.info(f"{message.author} boosted {message.guild.name}")

        embed = discord.Embed()
        embed.color = 0xF47FFF
        embed.title = "New booster"
        embed.description = (
            f"{message.author.mention} [boosted]({message.jump_url}) the server. "
            f"We're now at {message.guild.premium_subscription_count} boosts."
        )

        channel = discord.utils.get(message.guild.channels, id=config.channels.nitro_log)
        if channel and not isinstance(channel, (discord.ForumChannel, discord.CategoryChannel)):
            await channel.send(content=message.author.mention, embed=embed)

        embed = discord.Embed()
        embed.color = 0xF47FFF
        embed.title = "A new booster appeared!"
        embed.description = (
            f"{message.author.mention}, thank you so much for the server boost! "
            f"We are now at {message.guild.premium_subscription_count} boosts! "
            f"You can create a new ticket in <#{config.channels.tickets}> "
            "with your desired role name, icon (must be transparent), "
            "and [hex color](https://www.google.com/search?q=hex+color) for a custom booster role."
        )
        embed.set_image(url="https://i.imgur.com/O8R98p9.gif")

        await message.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """
        Send an embed in #nitro-logs when a boost was lost.
        """
        if not before.premium_since or after.premium_since:
            return

        logger.info(f"{after} stopped boosting {after.guild.name}")

        embed = discord.Embed()
        embed.color = 0xF47FFF
        embed.title = "Lost booster"
        embed.description = (
            f"{after.mention} no longer boosts the server. "
            f"We're now at {after.guild.premium_subscription_count} boosts."
        )

        channel = discord.utils.get(after.guild.channels, id=config.channels.nitro_log)
        if channel and not isinstance(channel, (discord.ForumChannel, discord.CategoryChannel)):
            await channel.send(content=after.mention, embed=embed)


async def setup(bot: commands.Bot) -> None:
    if config.channels.nitro_log:
        await bot.add_cog(BoostCog(bot))
