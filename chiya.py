import asyncio
import glob

import discord
from discord.ext import commands

import background
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

    print("Done loading cogs.")


async def on_member_join(self, member):
    guild = member.guild
    if guild.system_channel is not None:
        to_send = 'Welcome {0.mention} to {1.name}!'.format(member, guild)
        await guild.system_channel.send(to_send)

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

    await bot.process_commands(message)   

if __name__ == '__main__':
    bot.loop.create_task(background.check_for_posts(bot))
    bot.run(config.BOT_TOKEN)
