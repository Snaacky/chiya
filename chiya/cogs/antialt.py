from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from chiya.utils import embeds


class AntiAltCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        if datetime.now(timezone.utc) - member.created_at < timedelta(days=183):

            user_embed = embeds.make_embed(
                title="Uh-oh, you've been kicked!",
                image_url="https://files.catbox.moe/vp5op4.gif",
                color=discord.Color.blurple(),
                fields=[
                    {"name": "Server:", "value": f"{member.guild.name}", "inline": True},
                    {"name": "Reason:", "value": "We do not allow new Discord accounts to participate in our community to avoid bots and alt accounts. Please switch to your main account or try again at a later date.", "inline": False},
                ],
            )

            try:
                await member.send(embed=user_embed)
            except (discord.Forbidden, discord.HTTPException):
                pass

            await member.kick(reason="Account <6 months old")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntiAltCog(bot))
