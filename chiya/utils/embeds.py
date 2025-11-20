# import datetime
from typing import Any

import discord
from discord.ext import commands


# def make_embed(
#     ctx: commands.Context[Any] | discord.Interaction | None = None,
#     author: bool | None = None,
#     title: str = "",
#     description: str = "",
#     title_url: str | None = None,
#     thumbnail_url: str | None = None,
#     image_url: str | None = None,
#     fields: list[Any] | None = None,
#     footer: str | None = None,
#     color=None,
#     timestamp=None,
# ) -> discord.Embed:
#     """
#     A wrapper for discord.Embed with added support for non-native attributes.
#     `color` can either be of type discord.Color or a hexadecimal value.
#     `timestamp` can either be a unix timestamp or a datetime object.
#     """

#     if not isinstance(color, (int, discord.colour.Colour)):
#         embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
#     else:
#         embed = discord.Embed(title=title, description=description, color=color)

#     if ctx and author:
#         if isinstance(ctx, commands.Context):
#             embed.set_author(icon_url=ctx.author.display_avatar, name=ctx.author.name)

#         if isinstance(ctx, discord.Interaction):
#             embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)

#     if title_url:
#         embed.url = title_url

#     if thumbnail_url:
#         embed.set_thumbnail(url=thumbnail_url)

#     if image_url:
#         embed.set_image(url=image_url)

#     if fields:
#         for field in fields:
#             name = field.get("name", "") or ""
#             value = field.get("value", "") or ""
#             inline = field["inline"] if isinstance(field["inline"], bool) else False
#             embed.add_field(name=name, value=value, inline=inline)

#     if footer:
#         embed.set_footer(text=footer)

#     if timestamp:
#         if isinstance(timestamp, int):
#             embed.timestamp = datetime.datetime.fromtimestamp(timestamp)
#         else:
#             embed.timestamp = timestamp

#     return embed


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
