import logging
import re

import privatebinapi

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot

import config
from utils import database
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class ArchiveCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_role(config.role_staff)
    @commands.before_invoke(record_usage)
    @commands.command(name="archive")
    async def archive(self, ctx):
        """ Log the existing modmail ticket to PrivateBin and delete the ticket channel."""

        # Fetch the ticket channel.
        channel = ctx.message.channel

        # Fetch the staff role.
        role_staff = discord.utils.get(ctx.guild.roles, id=config.role_staff)

        # Fetch the trial mod role.
        role_trial_mod = discord.utils.get(ctx.guild.roles, id=config.role_trial_mod)

        # Warns if the ticket close command is called outside of the ticket channel.
        if not channel.category_id == config.ticket_category_id or "ticket" not in channel.name:
            await embeds.error_message(ctx=ctx, description="You can only run this command in active ticket channels.")
            return

        # Loop through the channel messages from old to new, breaking at the very first embed.
        ticket_creator = ""
        ticket_topic = ""
        utc_time = ""
        async for message in ctx.channel.history(oldest_first=True):

            # If the message author is a bot and the message is also an embed.
            if message.author.bot and message.embeds:

                # Re-format the UTC time before adding it to the database by removing the millisecond to match with the
                # PrivateBin log format as well as other entries in the database.
                utc_time = str(message.created_at).split(".")[-2]
                embed = message.embeds

                # Make the embed a dictionary and target the ticket creator and topic field.
                for strings in embed:
                    dictionary = strings.to_dict()
                    ticket_creator = dictionary["fields"][0]["value"]
                    ticket_topic = dictionary["fields"][1]["value"]
                break

        # Send notice that the channel will be archived.
        embed = embeds.make_embed(author=False, color=0x00ffdf)
        embed.title = f"The ticket has been archived."
        await ctx.send(embed=embed)

        # Remove the <@> part in the ticket creator ID string.
        ticket_creator = re.sub("[^0-9]", "", ticket_creator)

        # Initialize the PrivateBin message log string.
        message_log = f"Ticket Creator ID: {ticket_creator}\nTicket Topic: {ticket_topic}\n\n"

        # Initialize a list of moderator ids as a set for no duplicates.
        mod_list = set()

        # Loop through all messages in the ticket from old to new.
        async for message in ctx.channel.history(oldest_first=True):

            # Ignore the bot replies.
            if not message.author.bot:

                # Time format is unnecessarily lengthy so trimming it down and keep the log go easier on the eyes.
                formatted_time = str(message.created_at).split(".")[-2]

                # Append the new messages to the current log as we loop.
                message_log += f"[{formatted_time}] {message.author}: {message.content}\n"

                # If the messenger has either staff role or trial mod role, add their ID to the mod_list set.
                if role_staff or role_trial_mod in message.author.roles:
                    mod_list.add(message.author.id)

        # Convert the set of participated mod IDs (mod_list) into a string to be used in the embed.
        participating_mods = ""
        for mod in mod_list:
            participating_mods += f"<@{mod}>\n"

        # Dump message log to private bin. This returns a dictionary, but only the url is needed for the embed.
        token = privatebinapi.send("https://bin.piracy.moe", text=message_log, expiration="never")
        url = token["full_url"]

        # Create the embed in #ticket-log.
        embed_log = embeds.make_embed(ctx=ctx, author=False, image_url=config.pencil, color=0x00ffdf)
        embed_log.title = f"{ctx.channel.name} archived"
        embed_log.add_field(name="Ticket Creator:", value=f"<@{ticket_creator}>", inline=False)
        embed_log.add_field(name="Ticket Topic:", value=ticket_topic, inline=False)
        embed_log.add_field(name="Participating Moderators:", value=participating_mods, inline=False)
        embed_log.add_field(name="Ticket Log: ", value=url, inline=False)

        # Send the embed to #ticket-log.
        ticket_log = discord.utils.get(ctx.guild.channels, id=config.ticket_log)
        await ticket_log.send(embed=embed_log)

        # Add the ticket to database.
        with dataset.connect(database.get_db()) as db:
            db["tickets"].insert(dict(
                user_id=ticket_creator, status="completed", guild="622243127435984927",
                dm_embed_id=None, timestamp=utc_time, ticket_topic=ticket_topic, log_url=url
            ))

        # Delete the channel.
        await ctx.channel.delete()


def setup(bot: Bot) -> None:
    """ Load the Ticket cog. """
    bot.add_cog(ArchiveCog(bot))
    log.info("Commands loaded: tickets")
