import datetime
from urllib.parse import urlparse

import discord
import httpx
from discord.ext import commands
from loguru import logger
from sqlalchemy import select

from chiya import db
from chiya.config import config
from chiya.models import Joyboard


class JoyboardCog(commands.Cog):
    JOYS = ("😂", "😹", "joy_pride", "joy_tone1", "joy_tone5", "joy_logga")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def generate_color(self, joy_count: int) -> int:
        """
        Hue, saturation, and value is divided by 360, 100, 100 respectively because it is using the
        fourth coordinate group described in
        https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Color/Normalized_Color_Coordinates#HSV_coordinates.
        """
        if joy_count <= 5:
            saturation = 0.4
        elif 6 <= joy_count <= 15:
            saturation = 0.4 + (joy_count - 5) * 0.06
        else:
            saturation = 1

        return discord.Color.from_hsv(48 / 360, saturation, 1).value

    async def get_joy_count(self, message: discord.Message) -> int:
        """Return the amount of joys that a message has, excluding the author of the message."""
        if not message.guild:
            return 0

        unique_users = set()
        for reaction in message.reactions:
            if not isinstance(reaction.emoji, (discord.PartialEmoji, discord.Emoji)):
                continue

            if not self.check_emoji(reaction.emoji, message.guild.id):
                continue

            async for user in reaction.users():
                if user.id != message.author.id:
                    unique_users.add(user.id)

        return len(unique_users)

    def check_emoji(self, emoji: discord.PartialEmoji | discord.Emoji, guild_id: int) -> bool:
        if isinstance(emoji, discord.PartialEmoji) and emoji.is_custom_emoji():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return False

            global_emoji = discord.utils.get(guild.emojis, id=emoji.id)
            if not global_emoji:
                return False

        elif isinstance(emoji, discord.Emoji):
            if emoji.guild_id is None:
                return False

            if emoji.guild_id != guild_id:
                return False

        name = emoji if isinstance(emoji, str) else emoji.name
        return name in self.JOYS or name.startswith("joy_")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if not payload.guild_id or not payload.member:
            return

        if not self.check_emoji(payload.emoji, payload.guild_id):
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

        if not message.guild or not isinstance(message.channel, discord.TextChannel):
            return

        time_since_message = datetime.datetime.now(datetime.timezone.utc) - message.created_at
        if time_since_message.days > config.joyboard.timeout:
            logger.info(
                f"{payload.member.name} reacted to a message from {time_since_message.days} days ago - #{message.channel.name}-{message.id}"
            )

        joy_count = await self.get_joy_count(message)

        if (
            message.author.bot
            or message.author.id == payload.member.id
            or payload.channel_id in config.joyboard.blacklisted
            or joy_count < config.joyboard.joy_limit
        ):
            return

        joyboard_channel = discord.utils.get(message.guild.channels, id=config.joyboard.channel_id)
        if not joyboard_channel or not isinstance(joyboard_channel, discord.TextChannel):
            return

        result = db.session.scalar(
            select(Joyboard).where(
                Joyboard.channel_id == payload.channel_id,
                Joyboard.message_id == payload.message_id,
            )
        )

        if result:
            try:
                joy_embed = await joyboard_channel.fetch_message(result.joy_embed_id)

                embed_dict = joy_embed.embeds[0].to_dict()
                embed_dict["color"] = self.generate_color(joy_count=joy_count)
                embed = discord.Embed.from_dict(embed_dict)

                await joy_embed.edit(
                    content=f"😂 **{joy_count}** {message.channel.mention}",
                    embed=embed,
                )

                return
            except discord.NotFound:  # Record is in database but the message/embed is missing from the channel.
                pass

        embed = discord.Embed()
        embed.color = self.generate_color(joy_count=joy_count)
        embed.description = f"{message.content}\n\n"
        embed.timestamp = datetime.datetime.now()
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar)
        embed.add_field(name="Source:", value=f"[Jump!]({message.jump_url})", inline=False)
        embed.set_footer(text=str(payload.message_id))

        images = []

        for attachment in message.attachments:
            embed.description += f"{attachment.url}\n"
            if attachment.content_type and "image" in attachment.content_type and not attachment.is_spoiler():
                images.append(attachment.url)

        for message_embed in message.embeds:
            # Other types may need to be added in future
            if message_embed.type in ["gif", "gifv"]:
                if message_embed.provider and message_embed.provider.url:
                    urlinfo = urlparse(message_embed.provider.url)
                    if urlinfo.netloc in ["tenor.com", "tenor.co"]:
                        async with httpx.AsyncClient() as client:
                            req = await client.head(f"{message_embed.url}.gif", follow_redirects=True)
                            images.append(req.url)
            elif message_embed.type in ["image"]:
                images.append(message_embed.url)

        # Prioritize the first image over sticker if possible.
        if images:
            embed.set_image(url=images[0])
        elif message.stickers:
            embed.set_image(url=message.stickers[0].url)

        joyed_message = await joyboard_channel.send(
            content=f"😂 **{joy_count}** {message.channel.mention}",
            embed=embed,
        )

        # Update the joy embed ID since the original one was probably deleted.
        if result:
            result.joy_embed_id = joyed_message.id
        else:
            new = Joyboard()
            new.channel_id = payload.channel_id
            new.message_id = payload.message_id
            new.joy_embed_id = joyed_message.id
            db.session.add(new)

        db.session.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = discord.utils.get(guild.text_channels, id=payload.channel_id)
        if not channel:
            return

        message = await channel.fetch_message(payload.message_id)
        if not message or not message.guild:
            return

        joyboard = discord.utils.get(guild.text_channels, id=config.joyboard.channel_id)
        if not joyboard:
            return

        if not self.check_emoji(payload.emoji, payload.guild_id):
            return

        result = db.session.scalar(
            select(Joyboard).where(
                Joyboard.channel_id == payload.channel_id,
                Joyboard.message_id == payload.message_id,
            )
        )

        if not result:
            return

        try:
            joy_embed = await joyboard.fetch_message(result.joy_embed_id)
        except discord.NotFound:
            joy_embed = None

        if not joy_embed:
            db.session.delete(result)
            db.session.commit()
            return

        joy_count = await self.get_joy_count(message)
        if joy_count < config.joyboard.joy_limit:
            db.session.delete(result)
            db.session.commit()
            await joy_embed.delete()

        embed_dict = joy_embed.embeds[0].to_dict()
        embed_dict["color"] = self.generate_color(joy_count=joy_count)
        embed = discord.Embed.from_dict(embed_dict)
        await joy_embed.edit(content=f"😂 **{joy_count}** {channel.mention}", embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload) -> None:
        """
        Automatically remove the joyboard embed if the message linked to it is deleted.
        """
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = discord.utils.get(guild.text_channels, id=config.joyboard.channel_id)
        if not channel:
            return

        result = db.session.scalar(
            select(Joyboard).where(
                Joyboard.channel_id == payload.channel_id,
                Joyboard.message_id == payload.message_id,
            )
        )

        if not result:
            return

        db.session.delete(result)
        db.session.commit()

        try:
            joy_embed = await channel.fetch_message(result.joy_embed_id)
            await joy_embed.delete()
        except discord.NotFound:
            return


async def setup(bot: commands.bot.Bot) -> None:
    await bot.add_cog(JoyboardCog(bot))
