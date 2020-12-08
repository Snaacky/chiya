import discord
import re
import config



async def is_owner(ctx):
    print(ctx.message.author)
    return ctx.message.author.id == config.OWNER_ID

def contains_link(message):
    regex = r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})"
    if (len(re.findall(regex, message.content))!=0):
        return True
    else:
        return False
