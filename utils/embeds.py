import discord
from discord.ext.commands import Context


def make_embed(title: str = None, description: str = None, context: Context = None, color ="default",
          image_url: str = None, author=True) -> discord.Embed:
    """General embed template

    Args:
        title (str, optional): Title of your embed. Defaults to None.
        description (str, optional): Secondary text of your embed. Defaults to None.
        context (Context, optional): Discord context object, needed for author and timestamps. Defaults to None.
        color (str, optional): Use a predefined name or use a hex color value. Defaults to 'dark_theme'.
        image_url (str, optional): URL for the side image of embed. Defaults to None.
        author (bool, optional): Whether or not you wish to set the author of embed. Defaults to True.

    Returns:
        discord.Embed: discord embed object
    """

    # This is a list of colors that can be referenced by name rather than by hex value.
    colors = dict(default=0x202225, black=0, teal=0x1abc9c, dark_teal=0x11806a, green=0x2ecc71, dark_green=0x1f8b4c, blue=0x3498db,
                  dark_blue=0x206694, purple=0x9b59b6, dark_purple=0x71368a, magenta=0xe91e63, dark_magenta=0xad1457,
                  gold=0xf1c40f, dark_gold=0xc27c0e, orange=0xe67e22, dark_orange=0xa84300, red=0xe74c3c,
                  dark_red=0x992d22, lighter_grey=0x95a5a6, dark_grey=0x607d8b, light_grey=0x979c9f,
                  darker_grey=0x546e7a, blurple=0x7289da, greyple=0x99aab5, dark_theme=0x36393F, nitro_pink=0xff73fa, 
                  blank=0x2f3136, quotes_grey=0x4f545c,
                  # Reddit colors:
                  reddit=0xff5700, orange_red=0xFF450, upvote=0xFF8b60, neutral=0xC6C6C6, 
                  downvote=0x9494FF, light_bg=0xEFF7FF, header=0xCEE3F8, ui_text=0x336699)

    # If the color given was a valid name, use the corresponding hex value, else assume the value is already in hex form.
    if isinstance(color, str) and color.lower() in colors:
        embed = discord.Embed(color=colors[color.lower()],
                        title=title, description=description)
    else:
        embed = discord.Embed(color=color,
                        title=title, description=description)

    # Setting the author field and setting their profile pic as the image.
    if author and context is not None:
        embed.set_author(icon_url=context.author.avatar_url,
                    name=str(context.author))

    # Setting the embed side image if a url was given.
    if image_url:
        embed.set_thumbnail(url=image_url)

    # Adding Timestamp for ease of tracking when embeds are posted.
    if context:
        # This try is because there is a bug in discordpy that the created_at value is in the message object but the message object does not exist in regular messages.
        try: 
            embed.timestamp = context.created_at
        except:
            embed.timestamp = context.message.created_at

    return embed


async def error_message(description: str, ctx: Context, author:bool=True):
    """Send basic error message

    Note:
        You must await this function

    Args:
        description (str): Error description.
        ctx (Context): Discord context object, needed for author and timestamps.
        author (bool, optional): Whether or not you wish to set the author of embed. Defaults to True.
    """
    await ctx.send(embed=make_embed(title="Error", description=f'📢 **{description}**', context=ctx, color='dark_red', author=author), delete_after=30)

def error_embed(title: str, description: str, ctx: Context, author:bool=True) -> discord.Embed:
    """ Make a basic error message embed

    Args:
        title (str): Name of error.
        description (str): Error description.
        ctx (Context): Discord context object, needed for author and timestamps.
        author (bool, optional): Whether or not you wish to set the author of embed. Defaults to True.

    Returns:
        discord.Embed: discord embed object.
    """
    return make_embed(title=f'Error: {title}', description=f'📢 **{description}**', context=ctx, color='dark_red', author=author)


async def warning_message(ctx: Context, description: str, author:bool=True):
    """ Send a basic warning message
    
    Note:
        You must await this function

    Args:
        description (str): Warning description
        ctx (Context): Discord context object, needed for author and timestamps.
        author (bool, optional): Whether or not you wish to set the author of embed. Defaults to True.
    """
    await ctx.send(embed=make_embed(title='WARNING', description=f'📢 **{description}**', context = ctx, color="dark_gold", author=author), delete_after=30)


def files_and_links_only(ctx: Context) -> discord.Embed:
    """Standard messsage for when files or links are only used in the channel

    Args:
        ctx (Context): Discord context object, needed for author and timestamps.

    Returns:
        discord.Embed: discord embed object.
    """

    embed = make_embed(description="This channel is for submissions only! All messages that do not contain an image or a link are automatically removed.", context=ctx, color="reddit")
    embed.set_footer(text="This message will self-destruct in 10 seconds.")
    return embed