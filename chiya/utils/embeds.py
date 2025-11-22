# import datetime
from typing import Any

import discord
from discord.ext import commands


async def send_interaction_message(ctx: discord.Interaction, embed: discord.Embed) -> None:
    if ctx.response.is_done():
        await ctx.followup.send(embed=embed, ephemeral=True)
    else:
        await ctx.response.send_message(embed=embed, ephemeral=True)


async def send_success(
    ctx: commands.Context[Any] | discord.Interaction,
    description: str,
    title: str = "Success",
) -> None:
    """Send a simple, self-destruct success message."""
    embed = discord.Embed(title=title, description=description, color=discord.Color.green())

    if isinstance(ctx, commands.Context):
        await ctx.send(embed=embed, delete_after=30)

    if isinstance(ctx, discord.Interaction):
        await send_interaction_message(ctx, embed)


async def send_error(
    ctx: commands.Context[Any] | discord.Interaction,
    description: str,
    title: str = "Error:",
) -> None:
    """Send a simple, self-destruct error message."""
    embed = discord.Embed(title=title, description=description, color=discord.Color.red())

    if isinstance(ctx, commands.Context):
        await ctx.send(embed=embed, delete_after=30)

    if isinstance(ctx, discord.Interaction):
        await send_interaction_message(ctx, embed)


async def send_warning(
    ctx: commands.Context[Any] | discord.Interaction,
    description: str,
    title: str = "Warning",
) -> None:
    """Send a simple, self-destruct warning message."""
    embed = discord.Embed(title=title, description=description, color=discord.Color.dark_gold())

    if isinstance(ctx, commands.Context):
        await ctx.send(embed=embed, delete_after=30)

    if isinstance(ctx, discord.Interaction):
        await send_interaction_message(ctx, embed)


def error_embed(
    ctx: commands.Context[Any] | discord.Interaction,
    description: str,
    title: str | None = None,
) -> discord.Embed:
    """Make a basic error message embed."""
    embed = discord.Embed()
    embed.title = title if title else "Error:"
    embed.description = description
    embed.color = discord.Color.red()

    if isinstance(ctx, commands.Context):
        embed.set_author(icon_url=ctx.author.display_avatar, name=ctx.author.name)
    elif isinstance(ctx, discord.Interaction):
        embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)

    return embed
