import asyncio
import glob
import os
import sys
import logging

import discord
from discord.ext import commands
from loguru import logger as log

import database
from chiya.config import config


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


@bot.event
async def on_ready() -> None:
    """
    Called when the client is done preparing the data received from Discord.
    """
    log.info(f"Logged in as: {str(bot.user)}")
    await bot.tree.sync(guild=discord.Object(config["guild_id"]))


async def main():
    await setup_logger()
    await load_cogs()
    await bot.start(config["bot"]["token"])


async def setup_logger():
    log_level = config["bot"]["log_level"]
    if not log_level:
        log_level = "NOTSET"
    log.remove()
    
    class InterceptHandler(logging.Handler):
        """
        Setup up an Interceptor class to redirect all logs from the standard logging library to loguru.
        """
        def emit(self, record: logging.LogRecord) -> None:
            # Get corresponding Loguru level if it exists.
            level: str | int
            try:
                level = log.level(record.levelname).name
            except ValueError:
                level = record.levelno

            log.opt(exception=record.exc_info).log(level, record.getMessage())

    discord.utils.setup_logging(handler=InterceptHandler(),level=logging.getLevelName(config["bot"]["log_level"]), root=False)

    fmt = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>"
    log.add(sys.stdout, format=fmt, level=log_level, backtrace=False)
    log.add(os.path.join("logs", "bot.log"), format=fmt, rotation="1 day")


async def load_cogs():
    for cog in glob.iglob(os.path.join("cogs", "**", "[!^_]*.py"), root_dir="chiya", recursive=True):
        await bot.load_extension(cog.replace("/", ".").replace("\\", ".").replace(".py", ""))


if __name__ == "__main__":
    database.Database().setup()
    asyncio.run(main())
