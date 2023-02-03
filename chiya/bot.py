import asyncio
import glob
import logging
import os

import discord
from discord.ext import commands

import __init__  # noqa
import database
from config import config


bot = commands.Bot(
    activity=discord.Activity(type=discord.ActivityType.listening, name=config["bot"]["status"]),
    case_insensitive=config["bot"]["case_insensitive"],
    command_prefix=config["bot"]["prefix"],
    help_command=None,
    intents=discord.Intents(
        messages=config["bot"]["intents"]["messages"],
        message_content=config["bot"]["intents"]["message_content"],
        guilds=config["bot"]["intents"]["guilds"],
        members=config["bot"]["intents"]["members"],
        bans=config["bot"]["intents"]["bans"],
        reactions=config["bot"]["intents"]["reactions"],
    ),
)
log = logging.getLogger(__name__)


@bot.event
async def on_ready() -> None:
    """
    Called when the client is done preparing the data received from Discord.
    """
    log.info(f"Logged in as: {str(bot.user)}")
    await bot.tree.sync(guild=discord.Object(config["guild_id"]))


async def main():
    for cog in glob.iglob(os.path.join("cogs", "**", "[!^_]*.py"), root_dir="chiya", recursive=True):
        await bot.load_extension(cog.replace("/", ".").replace("\\", ".").replace(".py", ""))
    await bot.start(config["bot"]["token"])

if __name__ == "__main__":
    database.Database().setup()
    asyncio.run(main())
