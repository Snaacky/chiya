import logging

import discord
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from utils import embeds
from utils.config import config


log = logging.getLogger(__name__)


class General(Cog):

    def __init__(self, bot: Bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="pfp",
        description="Gets the members profile picture",
        guild_ids=[config["guild_id"]]
    )
    async def pfp(self, ctx: SlashContext, user: discord.User = None):
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

    @cog_ext.cog_slash(
        name="vote",
        description="Adds the vote reactions to a message",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="message",
                description="The ID for the target message",
                option_type=3,
                required=True
            ),
        ],
        default_permission=False,
        permissions={
            config["guild_id"]: [
                create_permission(config["roles"]["staff"], SlashCommandPermissionType.ROLE, True),
                create_permission(config["roles"]["trial_mod"], SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def vote(self, ctx, message: discord.Message = None):
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


def setup(bot: Bot) -> None:
    bot.add_cog(General(bot))
    log.info("Commands loaded: general")
