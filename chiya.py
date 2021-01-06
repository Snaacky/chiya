import glob
import logging

import discord
from discord.ext import commands

import __init__
from tasks import background
import config
from utils import embeds
from utils.utils import contains_link, has_attachment

bot = commands.Bot(
    command_prefix=config.PREFIX,
    intents=discord.Intents(messages=True, guilds=True, members=True),
    case_insensitive=True)
log = logging.getLogger(__name__)

@bot.event
async def on_ready():
    """Called when the client is done preparing the data received from Discord.

    For more information:
    https://discordpy.readthedocs.io/en/stable/api.html#discord.on_ready
    """
    print(f"Logged in as: {bot.user.name}#{bot.user.discriminator}")
    print(f"discord.py version: {discord.__version__}\n")

    # Adding in a activity message when the bot begins.
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{config.PREFIX}help"
        )
    )


@bot.event
async def on_member_join(self, member):
    # Defining for future use but removed previous unused code.
    """Called when a Member leaves or joins a Guild.

    Parameters:
        member – The Member that joined or left.

    For more information:
    https://discordpy.readthedocs.io/en/stable/api.html#discord.on_member_join
    """
    return


@bot.event
async def on_member_update(before, after):
    """ Event listener which is called when a member updates their profile.

    Parameters:
        before (discord.Member): The updated member’s old info.
        after (discord.Member): The updated member’s updated info.
    """
    # Defining for future use, below is a psuedo on_nitro_boost event.
    if before.premium_since is None and after.premium_since is not None:
        return


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    """Event Listener which is called when a message is edited.

    Note:
        This requires Intents.messages to be enabled.

    Parameters:
        before (discord.Message): The previous version of the message.
        after (discord.Message): The current version of the message.

    For more information:
        https://discordpy.readthedocs.io/en/stable/api.html#discord.on_message_edit
    """
    # Act as if its a new message rather than an a edit.
    await on_message(after)


@bot.event
async def on_message(ctx: discord.ext.commands.Context):
    """Event Listener which is called when a Message is created and sent.

    Note:
        This requires Intents.messages to be enabled.

    Warning:
        Your bot’s own messages and private messages are sent through this event.

    Parameters:
        ctx (discord.ext.commands.Context): A Message of the current message.

    For more information:
        https://discordpy.readthedocs.io/en/stable/api.html#discord.on_message
    """
    # Remove messages that don't contain links or files from our submissions only channels.
    if ctx.channel.id in config.SUBMISSION_CHANNEL_IDs and not (contains_link(ctx) or has_attachment(ctx)):
        # Ignore messages from all bots (this includes itself).
        if ctx.author.bot:
            return

        # Deletes message and sends a self-destructing warning embed.
        await ctx.delete()
        await ctx.channel.send(embed=embeds.files_and_links_only(ctx), delete_after=10)
    else:
        # If message does not follow with the above code, treat it as a potential command.
        await bot.process_commands(ctx)


if __name__ == '__main__':
    # Recursively loads in all the cogs in the folder named cogs.
    # Skips over any cogs that start with '__' or do not end with .py.
    for cog in glob.iglob("cogs/**/[!^_]*.py", recursive=True):
        if "\\" in cog:  # Fix pathing on Windows
            bot.load_extension(cog.replace("\\", ".")[:-3])
        else:  # Fix pathing on Linux:
            bot.load_extension(cog.replace("/", ".")[:-3])

    # Load backgound tasks.
    # TODO: Execute all files in the tasks folder and run in background.
    bot.loop.create_task(background.check_for_posts(bot))

    # Finally, run the bot.
    bot.run(config.BOT_TOKEN)
