import glob
import logging
import os

import discord
from discord.ext import commands

import __init__  # noqa
import database
from config import config


bot = commands.Bot(
    command_prefix=config["bot"]["prefix"],
    intents=discord.Intents(
        messages=config["bot"]["intents"]["messages"],
        message_content=config["bot"]["intents"]["message_content"],
        guilds=config["bot"]["intents"]["guilds"],
        members=config["bot"]["intents"]["members"],
        bans=config["bot"]["intents"]["bans"],
        reactions=config["bot"]["intents"]["reactions"],
        auto_moderation_configuration=config["bot"]["intents"]["automod"]
    ),
    case_insensitive=config["bot"]["case_insensitive"],
    help_command=None,
)
log = logging.getLogger(__name__)


@bot.event
async def on_ready() -> None:
    """
    Called when the client is done preparing the data received from Discord.
    """
    log.info(f"Logged in as: {str(bot.user)}")

    # TODO: Apparently changing presence in on_ready is bad practice and can result in connection interruption?
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name=config["bot"]["status"])
    )

    # TODO: Move this to an admin command rather than running every time the bot loads.
    # await bot.register_commands()


if __name__ == "__main__":
    for cog in glob.iglob(os.path.join("cogs", "**", "[!^_]*.py"), root_dir="chiya", recursive=True):
        bot.load_extension(cog.replace("/", ".").replace("\\", ".").replace(".py", ""))
    database.Database().setup()
    bot.run(config["bot"]["token"])
