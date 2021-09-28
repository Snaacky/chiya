import glob
import logging

import discord
from discord.ext import commands
from discord_slash import SlashCommand

import __init__
import utils.database
from utils.settings import settings

log = logging.getLogger(__name__)

bot = commands.Bot(
    command_prefix=settings["bot"]["prefix"],
    intents=discord.Intents(
        messages=settings["bot"]["intents"]["messages"], 
        guilds=settings["bot"]["intents"]["guilds"], 
        members=settings["bot"]["intents"]["members"], 
        bans=settings["bot"]["intents"]["bans"], 
        reactions=settings["bot"]["intents"]["reactions"]
    ),
    case_insensitive=settings["bot"]["case_insensitive"]
)

slash = SlashCommand(
    bot, 
    sync_commands=settings["bot"]["sync_commands"],
    sync_on_cog_reload=settings["bot"]["sync_on_cog_reload"],
)

@bot.event
async def on_ready():
    """Called when the client is done preparing the data received from Discord.

    For more information:
    https://discordpy.readthedocs.io/en/stable/api.html#discord.on_ready
    """
    log.info(f"Logged in as: {bot.user.name}#{bot.user.discriminator}")

    # Adding in a activity message when the bot begins.
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="your command!"
        )
    )

@bot.event
async def on_message(message: discord.Message):
    """This event listener has been moved to message_updates.py

    Unfortunately, this listener has to remain and do nothing, otherwise,
    any message will be ran twice and cause issues. Lame, i know
    """
    # Do nothing

if __name__ == '__main__':
    # Attempt to create the db, tables, and columns for Chiya.
    utils.database.Database().setup()

    # Recursively loads in all the cogs in the folder named cogs.
    # Skips over any cogs that start with '__' or do not end with .py.
    for cog in glob.iglob("cogs/**/[!^_]*.py", recursive=True):
        if "\\" in cog:  # Fix pathing on Windows.
            bot.load_extension(cog.replace("\\", ".")[:-3])
        else:  # Fix pathing on Linux.
            bot.load_extension(cog.replace("/", ".")[:-3])

    # Run the bot with the token as an environment variable.
    bot.run(settings["bot"]["token"])
