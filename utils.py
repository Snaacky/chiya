import discord

import config


async def is_owner(ctx):
    print(ctx.message.author)
    return ctx.message.author.id == config.OWNER_ID
