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
    async def pfp(
        self,
        ctx: context.ApplicationContext,
        user: Option(discord.User, description="User whose avatar will be grabbed", required=False),
        guild_avatar: Option(bool, description="Do you want their server specific avatar", required=False)
    ) -> bool:
        """
        Grab a user's avatar and return it in a large-sized embed.

        If the user parameter is not specified, the function will grab the invokers avatar instead.
        Offers the ability to attempt to grab a users server avatar and will fallback to their global
        avatar with a warning attached if a server specific avatar is not set.
        """
        await ctx.defer()

        user = user or ctx.author
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        embed = embeds.make_embed()
        if guild_avatar and hasattr(user, "guild_avatar"):
            embed.set_author(icon_url=user.guild_avatar, name=str(user))
            embed.set_image(url=user.guild_avatar)
        elif guild_avatar and not hasattr(user, "guild_avatar"):
            embed.set_author(icon_url=user.avatar.url, name=str(user))
            embed.set_image(url=user.avatar.url)
            embed.set_footer(text="⚠️ Warning: Could not find server avatar, defaulted to global avatar.")
        else:
            embed.set_author(icon_url=user.avatar.url, name=str(user))
            embed.set_image(url=user.avatar.url)
        await ctx.send_followup(embed=embed)

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
