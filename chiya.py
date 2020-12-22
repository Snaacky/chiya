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
    print(
        f"\n\nLogged in as: {bot.user.name} - {bot.user.id}\nDiscord.py Version: {discord.__version__}\n")
    print(f"Successfully logged in and booted...!")

    # Adding in a activity message when the bot begins
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{config.PREFIX}help",
            url="https://www.reddit.com/r/animepiracy",
            start=bot.user.created_at,
            details = f"Type {config.PREFIX}help to view all bot's commands and features."
        )
    )


async def on_member_join(self, member):
    guild = member.guild
    if guild.system_channel is not None:
        to_send = 'Welcome {0.mention} to {1.name}!'.format(member, guild)
        await guild.system_channel.send(to_send)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    """Event Listener which is called when a message is edited.

        For more information:
        https://discordpy.readthedocs.io/en/rewrite/api.html#discord.on_message_edit
    """
    # Act as if its a new message rather than an a edit
    await on_message(after)


@bot.event
async def on_message(ctx):
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
        #log.info("  -> " + cog.replace("\\", ".")[:-3])
        bot.load_extension(cog.replace("\\", ".")[:-3])

    bot.loop.create_task(background.check_for_posts(bot))
    bot.run(config.BOT_TOKEN)
