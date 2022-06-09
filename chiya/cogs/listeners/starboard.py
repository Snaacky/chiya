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

    @staticmethod
    def generate_color(star_count: int) -> int:
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

    @staticmethod
    def generate_star(star_count: int) -> str:
        if star_count <= 5:
            return "⭐"
        elif 6 <= star_count <= 10:
            return "🌟"
        elif 11 <= star_count <= 25:
            return "💫"
        else:
            return "✨"

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        If a message was reacted with 5 or more stars, send an embed to the starboard channel, as well as update the star
        count in the embed if more stars were reacted.
        """
        stars = ("⭐", "🌟", "💫", "✨")
        if payload.emoji.name not in stars:
            return

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

        star_count = 0
        for reaction in message.reactions:
            star_count += reaction.count if reaction.emoji in stars else 0

        if (
            message.author.bot
            or message.author.id == payload.member.id
            or payload.channel_id in config["channels"]["starboard"]["blacklisted"]
            or star_count < config["channels"]["starboard"]["star_limit"]
        ):
            return

        starboard_channel = discord.utils.get(message.guild.channels, id=config["channels"]["starboard"]["channel_id"])

        db = database.Database().get()
        result = db["starboard"].find_one(channel_id=payload.channel_id, message_id=payload.message_id)

        if result:
            try:
                msg = await starboard_channel.fetch_message(result["star_embed_id"])
                embed_dict = msg.embeds[0].to_dict()
                embed_dict["color"] = self.generate_color(star_count=star_count)
                embed = discord.Embed.from_dict(embed_dict)
                return await msg.edit(
                    content=f"{self.generate_star(star_count)} **{star_count}** {message.channel.mention}",
                    embed=embed,
                )
            except discord.NotFound:
                pass

        embed = embeds.make_embed(
            color=self.generate_color(star_count=star_count),
            footer=payload.message_id,
            timestamp=datetime.datetime.now(),
            fields=[{"name": "Source:", "value": f"[Jump!]({message.jump_url})", "inline": False}],
        )

        description = f"{message.content}\n\n"
        for attachment in message.attachments:
            description += f"{attachment.url}\n"
            # Must be of image MIME type. `content_type` will fail otherwise (NoneType).
            if attachment.content_type and "image" in attachment.content_type:
                embed.set_image(url=attachment.url)

        embed.description = description
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar)

        starred_message = await starboard_channel.send(
            content=f"{self.generate_star(star_count)} **{star_count}** {message.channel.mention}", embed=embed
        )

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

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """
        Update the star count in the embed if the stars were reacted. Delete star embed if the message has no star reacts.
        """
        stars = ("⭐", "🌟", "💫", "✨")
        if payload.emoji.name not in stars:
            return

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

        db = database.Database().get()
        result = db["starboard"].find_one(channel_id=payload.channel_id, message_id=payload.message_id)

        if not result:
            return

        starboard_channel = discord.utils.get(message.guild.channels, id=config["channels"]["starboard"]["channel_id"])

        try:
            msg = await starboard_channel.fetch_message(result["star_embed_id"])
        except discord.NotFound:
            return

        if not message.reactions:
            db["starboard"].delete(channel_id=payload.channel_id, message_id=payload.message_id)
            db.commit()
            db.close()
            return await msg.delete()

        star_count = 0
        for reaction in message.reactions:
            star_count += reaction.count if reaction.emoji in stars else 0

        embed_dict = msg.embeds[0].to_dict()
        embed_dict["color"] = self.generate_color(star_count=star_count)
        embed = discord.Embed.from_dict(embed_dict)
        await msg.edit(
            content=f"{self.generate_star(star_count)} **{star_count}** {message.channel.mention}", embed=embed
        )


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(Starboard(bot))
    log.info("Listener loaded: starboard")
