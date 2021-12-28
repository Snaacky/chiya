import logging

import discord
from discord.commands import Option, context, permissions, slash_command
from discord.ext import commands

from utils import embeds
from utils.config import config


log = logging.getLogger(__name__)


class GeneralCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_ids=config["guild_ids"], description="Gets the members profile picture")
    async def pfp(self, ctx: context.ApplicationContext, user: Option(discord.User, required=True)):
        """
        Returns the profile picture of the invoker or the mentioned user.

        Args:
            ctx (context.ApplicationContext): The context of the slash command.
            user (discord.User): The user to load the pfp from.
        """
        await ctx.defer()

        user = user or ctx.author

        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        if ctx.author:
            embed = embeds.make_embed(ctx=ctx)

        if user:
            embed = embeds.make_embed()
            embed.set_author(icon_url=user.avatar.url, name=str(user))

        embed.set_image(url=user.avatar.url)
        await ctx.send_followup(embed=embed)

    @slash_command(guild_ids=config["guild_ids"], default_permission=False)
    @permissions.has_role(config["roles"]["staff"])
    async def vote(
        self,
        ctx: context.ApplicationContext,
        message: Option(str, description="The ID for the target message", required=False)
    ):
        """
        Add vote reactions to a message.

        Args:
            ctx (context.ApplicationContext): The context of the slash command.
            message (str): The message ID to be voted.

        Raises:
            discord.NotFound: The entered string does not match any message ID.
        """
        await ctx.defer()

        if message:
            try:
                message = await ctx.channel.fetch_message(message)
            except discord.NotFound:
                return await embeds.error_message(ctx=ctx, description="Invalid message ID.")

        if not message:
            messages = await ctx.channel.history(limit=2).flatten()
            message = messages[1]

        await message.add_reaction(":yes:778724405333196851")
        await message.add_reaction(":no:778724416230129705")

        # We need to send something so the bot doesn't return "This interaction failed".
        delete = await ctx.send_followup("** **")
        await delete.delete()


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(GeneralCommands(bot))
    log.info("Commands loaded: general")
