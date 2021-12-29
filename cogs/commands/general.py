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

    @slash_command(guild_ids=config["guild_ids"], description="Gets a users profile picture")
    async def pfp(self, ctx: context.ApplicationContext, user: Option(discord.User, required=False)) -> bool:
        """
        Gets a users Discord profile picture (global, not server-specific).

        If the user argument is specified, it will return that users profile picture.
        Otherwise, it will return the invokers profile picture.

        Args:
            ctx (context.ApplicationContext): The context for the function invoke.
            user (discord.User, optional): The user to get the profile picture for.

        Returns:
            True (bool): If the profile picture was successfully grabbed.
        """
        # TODO: add an optional boolean to get the server specific pfp
        # TODO: what happens if a user ID is specified and that user ID is invalid?
        await ctx.defer()

        user = user or ctx.author

        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        # TODO: this if-statement logic can probably be optimized
        if ctx.author:
            embed = embeds.make_embed(ctx=ctx)

        if user:
            embed = embeds.make_embed()
            embed.set_author(icon_url=user.avatar.url, name=str(user))

        embed.set_image(url=user.avatar.url)
        await ctx.send_followup(embed=embed)
        return True

    @slash_command(guild_ids=config["guild_ids"], default_permission=False, description="Add vote reactions to a message.")
    @permissions.has_role(config["roles"]["staff"])
    async def vote(
        self,
        ctx: context.ApplicationContext,
        message: Option(str, description="The ID for the target message", required=False)
    ) -> bool:
        """
        Adds vote emojis (yes and no) reactions to a message.

        If the message argument is specified, it will add the reactions to that message.
        Otherwise, it will add the reactions to the last message in the channel.

        Args:
            ctx (context.ApplicationContext): Context for the function invoke.
            message (str, optional): Message ID to add the vote reactions to.

        Returns:
            True (bool): Vote reactions were successfully added.
            False (bool): Message ID provider does not exist, unsuccessful.
        """
        # TODO: what happens if the user doesn't have permission to add reactions in that channel?
        await ctx.defer()

        if message:
            try:
                message = await ctx.channel.fetch_message(message)
            except discord.NotFound:
                await embeds.error_message(ctx=ctx, description="Invalid message ID.")
                return False

        if not message:
            messages = await ctx.channel.history(limit=2).flatten()
            message = messages[1]

        # TODO: replace this with emotes grabbed from config
        await message.add_reaction(":yes:778724405333196851")
        await message.add_reaction(":no:778724416230129705")

        # We need to send something so the bot doesn't return "This interaction failed".
        # TODO: change this to a hidden success notification instead
        delete = await ctx.send_followup("** **")
        await delete.delete()
        return True


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(GeneralCommands(bot))
    log.info("Commands loaded: general")
