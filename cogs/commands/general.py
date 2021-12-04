import logging

import discord
from discord.ext import commands
from discord.commands import Option, permissions, slash_command, context

from utils import embeds
from utils.config import config


log = logging.getLogger(__name__)


class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_id=config["guild_id"], description="Gets the members profile picture")
    async def pfp(
        self,
        ctx: context.ApplicationContext,
        user: Option(discord.User, required=True)
    ):
        """ Returns the profile picture of the invoker or the mentioned user. """
        await ctx.defer()

        user = user or ctx.author

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        if ctx.author:
            embed = embeds.make_embed(ctx=ctx)

        if user:
            embed = embeds.make_embed()
            embed.set_author(icon_url=user.avatar, name=str(user))

        embed.set_image(url=user.avatar)
        await ctx.send(embed=embed)

    @slash_command(guild_id=config["guild_id"], default_permission=False)
    @permissions.has_role(config["roles"]["privileged"]["staff"])
    async def vote(
        self,
        ctx,
        message: Option(discord.User, description="The ID for the target message", required=True)
    ):
        """ Add vote reactions to a message. """
        await ctx.defer()

        if message:
            message = await ctx.channel.fetch_message(message)

        if not message:
            messages = await ctx.channel.history(limit=1).flatten()
            message = messages[0]

        await message.add_reaction(":yes:778724405333196851")
        await message.add_reaction(":no:778724416230129705")

        # We need to send *something* so the bot doesn't return "This interaction failed"
        delete = await ctx.send("** **")
        await delete.delete()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(General(bot))
    log.info("Commands loaded: general")
