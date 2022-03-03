import datetime

import discord
from discord.commands import context


def make_embed(
    ctx: context.ApplicationContext = None,
    author: bool = None,
    title: str = "",
    description: str = "",
    title_url: str = None,
    thumbnail_url: str = None,
    image_url: str = None,
    fields: list = None,
    footer: str = None,
    color=None,
    timestamp=None,
) -> discord.Embed:
    """
    A wrapper for discord.Embed with added support for non-native attributes.

    `color` can either be of type discord.Color or a hexadecimal value.
    `timestamp` can either be a unix timestamp or a datetime object.
    """

    if not isinstance(color, (int, discord.colour.Colour)):
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
    else:
        embed = discord.Embed(title=title, description=description, color=color)

    if ctx and author:
        embed.set_author(icon_url=ctx.author.avatar.url, name=ctx.author.name)

    if title_url:
        embed.url = title_url

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    if image_url:
        embed.set_image(url=image_url)

    if fields:
        for field in fields:
            name = field.get("name", "​")
            value = field.get("value", "​")
            inline = field["inline"] if isinstance(field["inline"], bool) else False
            embed.add_field(name=name, value=value, inline=inline)

    if footer:
        embed.set_footer(text=footer)

    if timestamp:
        if isinstance(timestamp, int):
            embed.timestamp = datetime.datetime.fromtimestamp(timestamp)
        else:
            embed.timestamp = timestamp

    return embed


async def success_message(ctx: context.ApplicationContext, description: str, title: str = None) -> None:
    """Send a simple, self-destruct success message."""
    embed = make_embed(title=title if title else "Success:", description=description, color=discord.Color.green())

    await ctx.send_followup(embed=embed, delete_after=30)


async def error_message(ctx: context.ApplicationContext, description: str, title: str = None) -> None:
    """Send a simple, self-destruct error message."""
    embed = make_embed(
        title=title if title else "Error:",
        description=description,
        color=discord.Color.red(),
    )

    await ctx.send_followup(embed=embed, delete_after=30)


async def warning_message(ctx: context.ApplicationContext, description: str, title: str = None) -> None:
    """Send a simple, self-destruct warning message."""
    embed = make_embed(
        title=title if title else "Warning:",
        description=description,
        color=discord.Color.dark_gold(),
    )

    await ctx.send_followup(embed=embed, delete_after=30)


def error_embed(ctx: context.ApplicationContext, title: str, description: str, author: bool = True) -> discord.Embed:
    """Make a basic error message embed."""
    return make_embed(
        ctx=ctx,
        title=title if title else "Error:",
        description=description,
        color=discord.Color.red(),
        author=author,
    )
