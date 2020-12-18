import discord


def make_embed(ctx: discord.ext.commands.Context=None, color='dark_theme', title: str = None, description: str = None,
          image_url: str = None, author=True) -> discord.Embed:
    """Global embed template"""

    # This is a list of colors that can be referenced by name rather than by hex value.
    colors = dict(default=0, teal=0x1abc9c, dark_teal=0x11806a, green=0x2ecc71, dark_green=0x1f8b4c, blue=0x3498db,
                  dark_blue=0x206694, purple=0x9b59b6, dark_purple=0x71368a, magenta=0xe91e63, dark_magenta=0xad1457,
                  gold=0xf1c40f, dark_gold=0xc27c0e, orange=0xe67e22, dark_orange=0xa84300, red=0xe74c3c,
                  dark_red=0x992d22, lighter_grey=0x95a5a6, dark_grey=0x607d8b, light_grey=0x979c9f,
                  darker_grey=0x546e7a, blurple=0x7289da, greyple=0x99aab5, dark_theme=0x36393F,
                  # Reddit colors:
                  reddit=0xff5700, orange_red=0xFF450, upvote=0xFF8b60, neutral=0xC6C6C6, 
                  downvote=0x9494FF, light_bg=0xEFF7FF, header=0xCEE3F8, ui_text=0x336699)

    # If the color given was a valid name, use the corresponding hex value, else assume the value is already in hex form.
    if color in colors:
        embed = discord.Embed(color=colors[color],
                        title=title, description=description)
    else:
        embed = discord.Embed(color=color,
                        title=title, description=description)

    # Setting the author field and setting their profile pic as the image.
    if author:
        embed.set_author(icon_url=ctx.author.avatar_url,
                    name=str(ctx.author))

    # Setting the embed side image if a url was given.
    if image_url:
        embed.set_thumbnail(url=image_url)

    # Adding Timestamp for ease of tracking when embeds are posted.
    try: # this try is because there is a bug in discordpy that the created_at value is in the message object but the message object does not exist in regular messages.
        embed.timestamp = ctx.created_at
    except:
        embed.timestamp = ctx.message.created_at

    return embed


async def error_message(ctx: discord.ext.commands.Context, description: str, author:bool=True):
    """Base Error message"""
    await ctx.send(embed=make_embed(ctx, color='dark_red', title='ERROR', description=f'📢 **{description}**', author=author))


async def warning_message(ctx: discord.ext.commands.Context, description: str, author:bool=True):
    """Base Warning message"""
    await ctx.send(embed=make_embed(ctx, color="dark_gold", title='WARNING', description=f'📢 **{description}**', author=author))


def files_and_links_only(ctx: discord.ext.commands.Context) -> discord.Embed:
    embed = make_embed(ctx, description="This channel is for submissions only! All messages that do not contain an image or a link are automatically removed.", color="reddit")
    embed.set_footer(text="This message will self-destruct in 10 seconds.")
    return embed