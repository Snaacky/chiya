from utils import contains_link
import discord
import glob
import sys

from discord.ext import commands

import config

cogs = ["cogs.settings"]
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='?', intents=intents)
bot_config = {
    "joins_channel": None,
    "leaves_channel": None,
    "count_channel": None
}


@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name}#{bot.user.discriminator}")
    print(f"Loaded cogs:")

    # Load each cog and print the cog loaded
    for cog in glob.glob("cogs/*.py"):
        bot.load_extension(f"cogs.{cog[5:-3]}")
        print(f"  -> {cog[5:-3]}")


async def on_member_join(self, member):
    guild = member.guild
    if guild.system_channel is not None:
        to_send = 'Welcome {0.mention} to {1.name}!'.format(member, guild)
        await guild.system_channel.send(to_send)

@bot.event
async def on_message(message):
    if (contains_link(message)):
        #actions


if __name__ == '__main__':
    bot.run(config.BOT_TOKEN)
