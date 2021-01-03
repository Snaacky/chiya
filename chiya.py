import asyncio
import glob
import logging


import discord
from discord.ext import commands

import __init__
from tasks import background
import config
from utils import embeds
from utils.utils import contains_link, has_attachment

log = logging.getLogger(__name__)

cogs = ["cogs.settings"]
intents = discord.Intents.default()
bot = commands.Bot(
    command_prefix=config.PREFIX,
    intents=intents,
    description="Chiya",
    case_insensitive=True)


@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name}#{bot.user.discriminator}")

    # Adding in a activity message when the bot begins
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{config.PREFIX}help"
        )
    )


@bot.event
async def on_member_join(self, member):
    # Defining for future use but removed unused code
    return


@bot.event
async def on_member_update(before, after):
    # Defining for future use, below is a psuedo on_nitro_boost event
    if before.premium_since is None and after.premium_since is not None:
        return


@bot.event
async def on_message(ctx):
    # TODO: This whole block can probably be moved into its own function
    # Remove messages that don't contain links or files from our submissions only channels
    if ctx.channel.id in config.SUBMISSION_CHANNEL_IDs and not (contains_link(ctx) or has_attachment(ctx)):
        # Ignore messages from self or bots to avoid loops and other oddities
        if ctx.author.id == bot.user.id or ctx.author.bot is True:
            return

        # Deletes message and send self-destructing warning embed
        await ctx.delete()
        warning = await ctx.channel.send(embed=embeds.files_and_links_only(ctx))
        await asyncio.sleep(10)
        await warning.delete()
    else:
        # If message does not follow with the above code, treat it as a potential command.
        await bot.process_commands(ctx)

if __name__ == '__main__':
    # filtered to only load .py files that do not start with '__'
    for cog in glob.iglob("cogs/**/[!^_]*.py", recursive=True):
        bot.load_extension(cog.replace("\\", ".")[:-3])

    bot.loop.create_task(background.check_for_posts(bot))
    bot.run(config.BOT_TOKEN)
