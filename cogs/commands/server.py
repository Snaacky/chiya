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
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    server = SlashCommandGroup(
        "server",
        "Server management commands",
        guild_ids=config["guild_ids"],
        default_permission=False,
        permissions=[permissions.Permission(id=config["roles"]["staff"], type=1, permission=True)],  # Type 1 is role, 2 is user.
    )

    @server.command(name="pop", description="Gets the current server population")
    async def pop(self, ctx: context.ApplicationContext):
        """
        Slash command for getting the current population of the server.

        Args:
            ctx (): The context of the slash command.
        """
        await ctx.defer()
        await ctx.send_followup(ctx.guild.member_count)

    @server.command(name="banner", description="Sets the banner to the image provided")
    async def banner(
        self,
        ctx: context.ApplicationContext,
        link: Option(str, description="The link to the image to be set", required=True),
    ):
        """
        Slash command for updating the server banner.

        Args:
            ctx (): The context of the slash command.
            link (): A direct link to the image to use for the update.
        """
        await ctx.defer()

        r = requests.get(url=link)

        if r.status_code != 200:
            return await embeds.error_message(
                ctx=ctx, description="The link you entered was not accessible."
            )

        try:
            await ctx.guild.edit(banner=r.content)
        except discord.InvalidArgument:
            return await embeds.error_message(
                ctx=ctx, description="Unable to set banner, verify the link is correct."
            )

        await ctx.send_followup(
            embed=embeds.make_embed(
                ctx=ctx,
                title="Banner updated",
                description=f"Banner [image]({link}) updated by {ctx.author.mention}",
                color="soft_green",
            )
        )

    @server.command(name="pingable", description="Makes a role pingable for 10 seconds")
    async def pingable(
        self,
        ctx: context.ApplicationContext,
        role: Option(discord.Role, description="The role to make pingable", required=True),
    ):
        """
        Slash command for making server roles temporarily pingable.

        Args:
            ctx (): The context of the slash command.
            role (): The role to be made temporarily pingable.
        """
        await ctx.defer()

        if role.mentionable:
            return await embeds.success_message(
                ctx, description="That role is already mentionable."
            )

        try:
            await role.edit(mentionable=True)
            await embeds.success_message(
                ctx, description="You have 10 seconds to ping the role."
            )
            await asyncio.sleep(10)
            await role.edit(mentionable=False)
        except discord.Forbidden:
            await embeds.error_message(ctx, description="The bot does not have permission to edit this role.")

    @server.command(name="boosters", description="List all the server boosters")
    async def boosters(self, ctx: context.ApplicationContext):
        """
        Slash command for getting the current list of server boosters.

        Args:
            ctx (Context): The context of the slash command.
        """
        await ctx.defer()

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Total boosts: {ctx.guild.premium_subscription_count}",
            thumbnail_url="https://i.imgur.com/22ZZG7h.png",
            color="nitro_pink",
            author=False,
        )
        embed.description = "\n".join(user.mention for user in ctx.guild.premium_subscribers)
        embed.set_footer(text=f"Total boosters: {len(ctx.guild.premium_subscribers)}")
        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ServerCommands(bot))
    log.info("Commands loaded: server")
