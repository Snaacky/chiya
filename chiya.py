import asyncio
import glob

import discord
from discord.ext import commands

import config
import embeds
from utils import contains_link, has_attachment

cogs = ["cogs.settings"]
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='?', intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name}#{bot.user.discriminator}")
    print("Loaded cogs:")

    # Load each cog and print the cog loaded
    for cog in glob.glob("cogs/*.py"):
        bot.load_extension(f"cogs.{cog[5:-3]}")
        print(f"  -> {cog[5:-3]}")


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


if __name__ == '__main__':
    bot.run(config.BOT_TOKEN)
