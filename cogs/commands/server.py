import asyncio
import logging

import discord
import requests
from discord.commands import Option, SlashCommandGroup, context, permissions
from discord.ext import commands

from utils import embeds
from utils.config import config


log = logging.getLogger(__name__)


class ServerCommands(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Permission type 1 is role and type 2 is user.
    server = SlashCommandGroup(
        "server",
        "Server management commands",
        guild_ids=config["guild_ids"],
        default_permission=False,
        permissions=[permissions.Permission(id=config["roles"]["staff"], type=1, permission=True)],
    )

    @server.command(name="pop", description="Gets the current server population")
    async def pop(self, ctx: context.ApplicationContext) -> None:
        """
        Send the current member count of the server.
        """
        await ctx.defer()
        await ctx.send_followup(ctx.guild.member_count)

    @server.command(name="banner", description="Sets the banner to the image provided")
    async def banner(
        self,
        ctx: context.ApplicationContext,
        link: Option(str, description="The link to the image to be set", required=True),
    ) -> None:
        """
        Update the banner of the guild. Return if the HTTP status code
        received is not 200 OK (invalid url).
        """
        await ctx.defer()

        r = requests.get(url=link)

        if r.status_code != 200:
            return await embeds.error_message(ctx=ctx, description="The link you entered was not accessible.")

        try:
            await ctx.guild.edit(banner=r.content)
        except discord.InvalidArgument:
            return await embeds.error_message(ctx=ctx, description="Unable to set banner, verify the link is correct.")

        embed = embeds.make_embed(
            title="Banner updated",
            description=f"Banner [image]({link}) updated by {ctx.author.mention}",
            color=discord.Color.green(),
        )

        await ctx.send_followup(embed=embed)

    @server.command(name="pingable", description="Makes a role pingable for 10 seconds")
    async def pingable(
        self,
        ctx: context.ApplicationContext,
        role: Option(discord.Role, description="The role to make pingable", required=True),
    ) -> None:
        """
        Make a role pingable for 10 seconds.
        """
        await ctx.defer()

        if role.mentionable:
            return await embeds.success_message(ctx=ctx, description="That role is already mentionable.")

        try:
            await role.edit(mentionable=True)
            await embeds.success_message(ctx=ctx, description="You have 10 seconds to ping the role.")
            await asyncio.sleep(10)
            await role.edit(mentionable=False)
        except discord.Forbidden:
            await embeds.error_message(ctx=ctx, description="The bot does not have permission to edit this role.")

    @server.command(name="boosters", description="List all the server boosters")
    async def boosters(self, ctx: context.ApplicationContext) -> None:
        """ Send an embed with all current server boosters. """
        await ctx.defer()

        embed = embeds.make_embed(
            title=f"Total boosts: {ctx.guild.premium_subscription_count}",
            description="\n".join(user.mention for user in ctx.guild.premium_subscribers),
            thumbnail_url="https://i.imgur.com/22ZZG7h.png",
            footer=f"Total boosters: {len(ctx.guild.premium_subscribers)}",
            color=discord.Color.nitro_pink(),
        )
        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ServerCommands(bot))
    log.info("Commands loaded: server")
