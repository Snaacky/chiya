import datetime
import logging

import discord
from discord.ext import commands

from chiya import config, database
from chiya.utils import embeds


log = logging.getLogger(__name__)


class Starboard(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reaction_add_cache = set()
        self.reaction_remove_cache = set()

    def generate_color(self, star_count: int) -> int:
        """
        Hue, saturation, and value is divided by 360, 100, 100 respectively because it is using the fourth coordinate group
        described in https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Color/Normalized_Color_Coordinates#HSV_coordinates.
        """
        if star_count <= 5:
            saturation = 0.4
        elif 6 <= star_count <= 15:
            saturation = 0.4 + (star_count - 5) * 0.06
        else:
            saturation = 1

        return discord.Color.from_hsv(48 / 360, saturation, 1).value

    def generate_star(self, star_count: int) -> str:
        if star_count <= 4:
            return "⭐"
        elif 5 <= star_count <= 9:
            return "🌟"
        elif 10 <= star_count <= 24:
            return "💫"
        else:
            return "✨"

    async def get_star_count(self, message: discord.Message, stars: tuple) -> int:
        unique_users = set()
        for reaction in message.reactions:
            if reaction.emoji not in stars:
                continue
            async for user in reaction.users():
                unique_users.add(user.id)

        return len(unique_users)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        If a message was reacted with 5 or more stars, send an embed to the starboard channel, as well as update the star
        count in the embed if more stars were reacted.

        Implements a cache to prevent race condition where if multiple stars were reacted on a message after it hits the
        star threshold and the IDs were not written to the database quickly enough, a duplicated star embed would be sent.
        """
        stars = ("⭐", "🌟", "💫", "✨")
        if payload.emoji.name not in stars:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        star_count = await self.get_star_count(message, stars)
        cache_data = (payload.message_id, payload.channel_id)

        if (
            message.author.bot
            or message.author.id == payload.member.id
            or channel.is_nsfw()
            or payload.channel_id in config["channels"]["starboard"]["blacklisted"]
            or star_count < config["channels"]["starboard"]["star_limit"]
            or cache_data in self.reaction_add_cache
        ):
            return

        self.reaction_add_cache.add(cache_data)

        starboard_channel = discord.utils.get(message.guild.channels, id=config["channels"]["starboard"]["channel_id"])

        db = database.Database().get()
        result = db["starboard"].find_one(channel_id=payload.channel_id, message_id=payload.message_id)

        if result:
            try:
                star_embed = await starboard_channel.fetch_message(result["star_embed_id"])
                embed_dict = star_embed.embeds[0].to_dict()
                embed_dict["color"] = self.generate_color(star_count=star_count)
                embed = discord.Embed.from_dict(embed_dict)
                db.close()
                self.reaction_add_cache.remove(cache_data)
                return await star_embed.edit(
                    content=f"{self.generate_star(star_count)} **{star_count}** {message.channel.mention}",
                    embed=embed,
                )
            # Star embed found in database but the actual star embed was deleted.
            except discord.NotFound:
                pass

        embed = embeds.make_embed(
            color=self.generate_color(star_count=star_count),
            footer=payload.message_id,
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

        # Prioritize the first image over sticker if possible.
        if images:
            embed.set_image(url=images[0])
        elif message.stickers:
            embed.set_image(url=message.stickers[0].url)

        embed.description = description
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar)

        starred_message = await starboard_channel.send(
            content=f"{self.generate_star(star_count)} **{star_count}** {message.channel.mention}",
            embed=embed,
        )

        # Update the star embed ID since the original one was probably deleted.
        if result:
            result["star_embed_id"] = starred_message.id
            db["starboard"].update(result, ["id"])
        else:
            data = dict(
                channel_id=payload.channel_id,
                message_id=payload.message_id,
                star_embed_id=starred_message.id,
            )
            db["starboard"].insert(data, ["id"])

        db.commit()
        db.close()
        self.reaction_add_cache.remove(cache_data)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """
        Update the star count in the embed if the stars were reacted. Delete star embed if the star count is below threshold.
        """
        stars = ("⭐", "🌟", "💫", "✨")
        cache_data = (payload.message_id, payload.channel_id)

        if (
            payload.emoji.name not in stars
            or cache_data in self.reaction_remove_cache
        ):
            return

        self.reaction_remove_cache.add(cache_data)

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

        db = database.Database().get()
        result = db["starboard"].find_one(channel_id=payload.channel_id, message_id=payload.message_id)

        if not result:
            db.close()
            self.reaction_remove_cache.remove(cache_data)
            return

        starboard_channel = discord.utils.get(message.guild.channels, id=config["channels"]["starboard"]["channel_id"])

        try:
            star_embed = await starboard_channel.fetch_message(result["star_embed_id"])
        except discord.NotFound:
            db.close()
            self.reaction_remove_cache.remove(cache_data)
            return

        star_count = await self.get_star_count(message, stars)

        if star_count < config["channels"]["starboard"]["star_limit"]:
            db["starboard"].delete(channel_id=payload.channel_id, message_id=payload.message_id)
            db.commit()
            db.close()
            self.reaction_remove_cache.remove(cache_data)
            return await star_embed.delete()

        embed_dict = star_embed.embeds[0].to_dict()
        embed_dict["color"] = self.generate_color(star_count=star_count)
        embed = discord.Embed.from_dict(embed_dict)
        await star_embed.edit(
            content=f"{self.generate_star(star_count)} **{star_count}** {message.channel.mention}",
            embed=embed,
        )

        db.close()
        self.reaction_remove_cache.remove(cache_data)


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(Starboard(bot))
    log.info("Listener loaded: starboard")
