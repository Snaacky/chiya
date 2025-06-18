import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from loguru import logger

from chiya import models  # noqa
from chiya.config import config, workspace

bot = commands.Bot(
    activity=discord.Activity(type=discord.ActivityType.listening, name=config.bot.status),
    case_insensitive=True,
    command_prefix=config.bot.prefix,
    help_command=None,
    intents=discord.Intents.all(),
)


@bot.event
async def on_ready() -> None:
    "Called when the client is done preparing the data received from Discord."
    logger.info(f"Logged in as: {str(bot.user)}")
    await bot.tree.sync(guild=discord.Object(config.guild_id))


async def main() -> None:
    await setup_logger()
    await load_cogs()
    await bot.start(config.bot.token)


async def setup_logger() -> None:
    log_folder = workspace / "logs"
    logger.remove()

    class InterceptHandler(logging.Handler):
        "Setup up an Interceptor class to redirect all logs from the standard logging library to loguru."

        def emit(self, record: logging.LogRecord) -> None:
            # Get corresponding Loguru level if it exists.
            level: str | int
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            logger.opt(exception=record.exc_info).log(level, record.getMessage())

    discord.utils.setup_logging(
        handler=InterceptHandler(), level=logging.getLevelNamesMapping().get(config.bot.log_level, "NOTSET"), root=False
    )

    fmt = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>"
    logger.add(sys.stdout, format=fmt, level=config.bot.log_level, backtrace=False)
    logger.add(log_folder / "bot.log", format=fmt, rotation="1 day")


async def load_cogs() -> None:
    folder = workspace / "chiya" / "cogs"
    for file in folder.glob("*.py"):
        await bot.load_extension(f"cogs.{file.stem}")
        logger.info(f"Cog loaded: {list(bot.cogs.keys())[-1]}")


if __name__ == "__main__":
    # Needed so the bot can run under Windows, see: https://github.com/aio-libs/aiodns/issues/86
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
