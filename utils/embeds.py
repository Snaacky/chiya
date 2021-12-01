import datetime

import discord
from discord_slash import SlashContext


def make_embed(ctx: SlashContext = None, title: str = "", description: str = "", color="default", title_url: str = None, thumbnail_url: str = None, image_url: str = None, author=True) -> discord.Embed:
    """General embed template

    Args:
        title (str, optional): Title of your embed. Defaults to None.
        description (str, optional): Secondary text of your embed. Defaults to None.
        ctx (Context, optional): Discord context object, needed for author and timestamps. Defaults to None.
        color (str, optional): Use a predefined name or use a hex color value. Defaults to 'dark_theme'.
        title_url (str, optional): URL to hyperlink the embed title to. Defaults to None.
        thumbnail_url (str, optional): URL for the side image of embed. Defaults to None.
        author (bool, optional): Whether or not you wish to set the author of embed. Defaults to True.

    Returns:
        discord.Embed: discord embed object
    """

    # This is a list of colors that can be referenced by name rather than by hex value.
    colors = dict(
        default=0x202225, black=0, teal=0x1abc9c, dark_teal=0x11806a, green=0x2ecc71, dark_green=0x1f8b4c,
        blue=0x3498db, dark_blue=0x206694, purple=0x9b59b6, dark_purple=0x71368a, magenta=0xe91e63,
        dark_magenta=0xad1457, gold=0xf1c40f, dark_gold=0xc27c0e, orange=0xe67e22, dark_orange=0xa84300,
        red=0xe74c3c, dark_red=0x992d22, lighter_grey=0x95a5a6, dark_grey=0x607d8b, light_grey=0x979c9f,
        darker_grey=0x546e7a, blurple=0x7289da, greyple=0x99aab5, dark_theme=0x36393F, nitro_pink=0xff73fa,
        blank=0x2f3136, quotes_grey=0x4f545c, soft_red=0xcd6d6d, soft_green=0x68c290, soft_orange=0xf9cb54,
        bright_green=0x01d277,
        # Reddit colors:
        reddit=0xff5700, orange_red=0xFF4500, upvote=0xFF8b60, neutral=0xC6C6C6,
        downvote=0x9494FF, light_bg=0xEFF7FF, header=0xCEE3F8, ui_text=0x336699
    )

    # Uuse the corresponding hex value if matching key, else assume the value is already in hex form.
    if isinstance(color, str) and color.lower() in colors:
        embed = discord.Embed(color=colors[color.lower()], title=title, description=description)
    else:
        embed = discord.Embed(color=color, title=title, description=description)

    # Setting the author field and setting their profile pic as the image.
    if author and ctx is not None:
        embed.set_author(icon_url=ctx.author.avatar_url, name=str(ctx.author))

    # Setting the embed side image if a url was given.
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    if image_url:
        embed.set_image(url=image_url)

    # Adding Timestamp for ease of tracking when embeds are posted.
    if ctx:
        embed.timestamp = datetime.datetime.utcnow()

    if title_url:
        embed.url = title_url

    return embed


async def success_message(ctx: SlashContext, description: str, title: str = None, author: bool = True):
    """Send basic sucess message

    Note:
        You must await this function

    Args:
        description (str): Success description.
        ctx (Context): Discord context object, needed for author and timestamps.
        author (bool, optional): Whether or not you wish to set the author of embed. Defaults to True.
    """
    title = "Success:" if not title else title
    embed = make_embed(title="Success:", description=description, color="soft_green", author=False)
    await ctx.send(embed=embed, delete_after=30)


async def error_message(ctx: SlashContext, description: str, title: str = None, author: bool = True):
    """Send basic error message

    Note:
        You must await this function

    Args:
        description (str): Error description.
        ctx (Context): Discord context object, needed for author and timestamps.
        author (bool, optional): Whether or not you wish to set the author of embed. Defaults to True.
    """
    title = "Error:" if not title else title
    embed = make_embed(title=title, description=description, color="soft_red", author=False)
    await ctx.send(embed=embed, delete_after=30)


async def warning_message(ctx: SlashContext, description: str, title: str = None, author: bool = True):
    """ Send a basic warning message

    Note:
        You must await this function

    Args:
        description (str): Warning description
        title (str, optional): Title to name the warning embed.
        ctx (Context): Discord context object, needed for author and timestamps.
        author (bool, optional): Whether or not you wish to set the author of embed. Defaults to True.
    """
    title = "Warning:" if not title else title
    await ctx.send(embed=make_embed(
        title=title,
        description=description,
        ctx=ctx,
        color="dark_gold",
        author=author
        ),
        delete_after=30
    )


def error_embed(ctx: SlashContext, title: str, description: str, author: bool = True) -> discord.Embed:
    """ Make a basic error message embed

    Args:
        title (str): Title to name the error embed.
        description (str): Error description.
        ctx (Context): Discord context object, needed for author and timestamps.
        author (bool, optional): Whether or not you wish to set the author of embed. Defaults to True.

    Returns:
        discord.Embed: discord embed object.
    """
    title = "Error:" if not title else title
    return make_embed(title=title, description=description, ctx=ctx, color="soft_red", author=author)
