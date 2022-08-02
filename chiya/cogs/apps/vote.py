import logging

import discord
import discord.utils
from discord import message_command
from discord.commands import context
from discord.ext import commands

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class VoteApp(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @message_command(guild_ids=config["guild_ids"], description="Add vote reactions to a message.")
    @commands.has_role(config["roles"]["staff"])
    async def vote(self, ctx: context.ApplicationContext, message: discord.Message) -> None:
        """
        Adds vote emojis (yes and no) reactions to a message.
        """
        # TODO: what happens if the user doesn't have permission to add reactions in that channel?
        await ctx.defer(ephemeral=True)

        if message:
            try:
                message = await ctx.channel.fetch_message(message)
            except discord.NotFound:
                return await embeds.error_message(ctx=ctx, description="Invalid message ID.")

        if not message:
            messages = await ctx.channel.history(limit=1).flatten()
            message = messages[0]

        emoji_yes = discord.utils.get(ctx.guild.emojis, id=config["emoji"]["yes"]) or "👍"
        emoji_no = discord.utils.get(ctx.guild.emojis, id=config["emoji"]["no"]) or "👎"

        await message.add_reaction(emoji_yes)
        await message.add_reaction(emoji_no)
        await embeds.success_message(ctx=ctx, description=f"Added votes to {message.jump_url}")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(VoteApp(bot))
    log.info("App loaded: vote")
