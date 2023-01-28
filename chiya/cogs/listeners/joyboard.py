import datetime
import logging
import httpx

import discord
from discord.ext import commands, tasks

from urllib.parse import urlparse

from chiya import config, database
from chiya.utils import embeds


log = logging.getLogger(__name__)


class Joyboard(commands.Cog):

    JOYS = ("😂", "😹", "joy_pride", "joy_tone1", "joy_tone5", "joy_logga")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cache = {"add": set(), "remove": set()}
        self.handle_reaction.start()

    def cog_unload(self) -> None:
        self.handle_reaction.cancel()

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
        unique_users = set()
        for reaction in message.reactions:
            if not self.check_emoji(reaction.emoji, message.guild.id):
                continue

            async for user in reaction.users():
                if not user.id == message.author.id:
                    unique_users.add(user.id)

        return len(unique_users)

    def check_emoji(self, emoji: discord.PartialEmoji | discord.Emoji, guild_id: int):
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

    reactions = {}

    @tasks.loop(seconds=5)
    async def handle_reaction(self, message_id):
        if not self.reactions:
            return

        payload: discord.RawReactionActionEvent
        for message, payload in self.reactions.items():
            del self.reactions[message]

            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            joy_count = await self.get_joy_count(message)

            if (
                message.author.bot
                or message.author.id == payload.member.id
                or channel.is_nsfw()
                or payload.channel_id in config["channels"]["joyboard"]["blacklisted"]
                or joy_count < config["channels"]["joyboard"]["joy_limit"]
            ):
                continue

            joyboard_channel = discord.utils.get(message.guild.channels, id=config["channels"]["joyboard"]["channel_id"])

            db = database.Database().get()
            result = db["joyboard"].find_one(channel_id=payload.channel_id, message_id=payload.message_id)

            if result:
                try:
                    joy_embed = await joyboard_channel.fetch_message(result["joy_embed_id"])
                    embed_dict = joy_embed.embeds[0].to_dict()
                    embed_dict["color"] = self.generate_color(joy_count=joy_count)
                    embed = discord.Embed.from_dict(embed_dict)
                    await joy_embed.edit(
                        content=f"😂 **{joy_count}** {message.channel.mention}",
                        embed=embed,
                    )
                    db.close()
                    continue
                # Joy embed found in database but the actual joy embed was deleted.
                except discord.NotFound:
                    pass

            embed = embeds.make_embed(
                color=self.generate_color(joy_count=joy_count),
                footer=str(payload.message_id),
                timestamp=datetime.datetime.now(),
                fields=[{"name": "Source:", "value": f"[Jump!]({message.jump_url})", "inline": False}],
            )

            description = f"{message.content}\n\n"

            images = []
            for attachment in message.attachments:
                description += f"{attachment.url}\n"
                # Must be of image MIME type. `content_type` will fail otherwise (NoneType).
                if "image" in attachment.content_type:
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

            # Prioritize the first image over sticker if possible.
            if images:
                embed.set_image(url=images[0])
            elif message.stickers:
                embed.set_image(url=message.stickers[0].url)

            embed.description = description
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar)

            joyed_message = await joyboard_channel.send(
                content=f"😂 **{joy_count}** {message.channel.mention}",
                embed=embed,
            )

            # Update the joy embed ID since the original one was probably deleted.
            if result:
                result["joy_embed_id"] = joyed_message.id
                db["joyboard"].update(result, ["id"])
            else:
                data = dict(
                    channel_id=payload.channel_id,
                    message_id=payload.message_id,
                    joy_embed_id=joyed_message.id,
                )
                db["joyboard"].insert(data, ["id"])

            db.commit()
            db.close()


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """
        If a message was reacted with 5 or more joys, send an embed to the joyboard channel, as well as update the joy
        count in the embed if more joys were reacted.

        Implements a cache to prevent race condition where if multiple joys were reacted on a message after it hits the
        joy threshold and the IDs were not written to the database quickly enough, a duplicated joy embed would be sent.
        """
        if not self.check_emoji(payload.emoji, payload.guild_id):
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if (
            message.author.bot
            or message.author.id == payload.member.id
            or channel.is_nsfw()
            or payload.channel_id in config["channels"]["joyboard"]["blacklisted"]
        ):
            return

        self.reactions[message.id] = payload

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """
        Update the joy count in the embed if the joys were reacted. Delete joy embed if the joy count is below threshold
        """
        cache_data = (payload.message_id, payload.channel_id)

        if (
            not self.check_emoji(payload.emoji, payload.guild_id)
            or cache_data in self.cache["remove"]
        ):
            return

        self.cache["remove"].add(cache_data)

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

        db = database.Database().get()
        result = db["joyboard"].find_one(channel_id=payload.channel_id, message_id=payload.message_id)

        if not result:
            self.cache["remove"].remove(cache_data)
            return db.close()

        joyboard_channel = discord.utils.get(message.guild.channels, id=config["channels"]["joyboard"]["channel_id"])

        try:
            joy_embed = await joyboard_channel.fetch_message(result["joy_embed_id"])
        except discord.NotFound:
            self.cache["remove"].remove(cache_data)
            return db.close()

        joy_count = await self.get_joy_count(message)

        if joy_count < config["channels"]["joyboard"]["joy_limit"]:
            db["joyboard"].delete(channel_id=payload.channel_id, message_id=payload.message_id)
            db.commit()
            db.close()
            self.cache["remove"].remove(cache_data)
            return await joy_embed.delete()

        embed_dict = joy_embed.embeds[0].to_dict()
        embed_dict["color"] = self.generate_color(joy_count=joy_count)
        embed = discord.Embed.from_dict(embed_dict)
        await joy_embed.edit(
            content=f"😂 **{joy_count}** {message.channel.mention}",
            embed=embed,
        )

        db.close()
        self.cache["remove"].remove(cache_data)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        """
        Automatically remove the joyboard embed if the message linked to it is deleted.
        """
        db = database.Database().get()
        result = db["joyboard"].find_one(channel_id=payload.channel_id, message_id=payload.message_id)

        if not result:
            return db.close()

        try:
            joyboard_channel = self.bot.get_channel(config["channels"]["joyboard"]["channel_id"])
            joy_embed = await joyboard_channel.fetch_message(result["joy_embed_id"])
            db["joyboard"].delete(channel_id=payload.channel_id, message_id=payload.message_id)
            db.commit()
            db.close()
            await joy_embed.delete()
        except discord.NotFound:
            db.close()


async def setup(bot: commands.bot.Bot) -> None:
    await bot.add_cog(Joyboard(bot))
    log.info("Listener loaded: joyboard")
