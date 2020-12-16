from utils import contains_link, has_attachment
import discord
import glob
import sys
import config
import background

from discord.ext import commands


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

    print("Done loading cogs.")

async def on_member_join(self, member):
    guild = member.guild
    if guild.system_channel is not None:
        to_send = 'Welcome {0.mention} to {1.name}!'.format(member, guild)
        await guild.system_channel.send(to_send)


@bot.event
async def on_message(message):
    if message.channel.id in config.SUBMISSION_CHANNEL_IDs and not (contains_link(message) or has_attachment(message)):
        print(message)
        await message.delete()

    await bot.process_commands(message)   

if __name__ == '__main__':
    bot.loop.create_task(background.check_for_posts(bot))
    bot.run(config.BOT_TOKEN)
