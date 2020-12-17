import discord


def files_and_links_only(ctx):
    embed = discord.Embed(description="This channel is for submissions only! All messages that do not contain an image or a link are automatically removed.")
    embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
    embed.set_footer(text="This message will self-destruct in 10 seconds.")
    return embed
