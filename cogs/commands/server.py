import asyncio
import logging
import requests

import discord
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from utils import embeds
from utils.config import config


log = logging.getLogger(__name__)


class Server(Cog):

    def __init__(self, bot: Bot):
        self.bot = bot

    @cog_ext.cog_subcommand(
        base="server",
        name="pop",
        description="Gets the current server population",
        guild_ids=[config["guild_id"]],
        base_default_permission=False,
        base_permissions={
            config["guild_id"]: [
                create_permission(config["roles"]["staff"], SlashCommandPermissionType.ROLE, True),
                create_permission(config["roles"]["trial_mod"], SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def pop(self, ctx: SlashContext):
        """
        Slash command for getting the current population of the server.

        Args:
            ctx (SlashContext): The context of the slash command.
        """
        await ctx.defer()
        await ctx.send(ctx.guild.member_count)

    @cog_ext.cog_subcommand(
        base="server",
        name="banner",
        description="Sets the banner to the image provided",
        guild_ids=[config["guild_id"]],
        base_default_permission=False,
        options=[
            create_option(
                name="link",
                description="The link to the image to be set",
                option_type=3,
                required=True
            )
        ]
    )
    async def banner(self, ctx: SlashContext, link: str):
        """
        Slash command for updating the server banner.

        Args:
            ctx (SlashContext): The context of the slash command.
            link (str): A direct link to the image to use for the update.
        """
        await ctx.defer()

        r = requests.get(url=link)

        if r.status_code != 200:
            return await embeds.error_message(ctx=ctx, description="The link you entered was not accessible.")

        try:
            await ctx.guild.edit(banner=r.content)
        except discord.errors.InvalidArgument:
            return await embeds.error_message(ctx=ctx, description="Unable to set banner, verify the link is correct.")

        await ctx.send(embed=embeds.make_embed(
            ctx=ctx,
            title="Banner updated",
            description=f"Banner [image]({link}) updated by {ctx.author.mention}",
            color="soft_green"
        ))

    @cog_ext.cog_subcommand(
        base="server",
        name="pingable",
        description="Makes a role pingable for 10 seconds",
        guild_ids=[config["guild_id"]],
        base_default_permission=False,
        options=[
            create_option(
                name="role",
                description="The role to make pingable",
                option_type=8,
                required=True
            )
        ]
    )
    async def pingable(self, ctx: SlashContext, role: discord.Role):
        """
        Slash command for making server roles temporarily pingable.

        Args:
            ctx (SlashContext): The context of the slash command.
            role (discord.Role): The role to be made temporarily pingable.
        """
        await ctx.defer()

        if role.mentionable:
            return await embeds.success_message(ctx, description="That role is already mentionable.")

        await role.edit(mentionable=True)
        await embeds.success_message(ctx, description="You have 10 seconds to ping the role.")
        await asyncio.sleep(10)
        await role.edit(mentionable=False)


def setup(bot: Bot) -> None:
    bot.add_cog(Server(bot))
    log.info("Commands loaded: server")
