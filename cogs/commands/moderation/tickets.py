import logging
import re
import time

import dataset
import discord
import privatebinapi
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from cogs.commands import settings
from utils import database
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class TicketCog(Cog):
    """ Ticket Cog """

    def __init__(self, bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="ticket",
        description="Opens a new modmail ticket",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="topic",
                description="A brief summary of the topic you would like to discuss",
                option_type=3,
                required=True
            )
        ]
    )
    async def open(self, ctx: SlashContext, topic: str):
        """ Opens a new modmail ticket."""
        await ctx.defer(hidden=True)

        # Check if a duplicate ticket already exists for the member.
        category = discord.utils.get(ctx.guild.categories, id=settings.get_value("category_tickets"))
        ticket = discord.utils.get(category.text_channels, name=f"ticket-{ctx.author.id}")

        # Throw an error and return if we found an already existing ticket.
        if ticket:
            await ctx.send(f"You already have a ticket open! {ticket.mention}", hidden=True)
            logging.info(f"{ctx.author} tried to create a new ticket but already had one open: {ticket}")
            return

        # Create a channel in the tickets category specified in settings.
        channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.id}", category=category)

        # Give both the staff and the user perms to access the channel. 
        await channel.set_permissions(discord.utils.get(ctx.guild.roles, id=settings.get_value("role_trial_mod")), read_messages=True)
        await channel.set_permissions(discord.utils.get(ctx.guild.roles, id=settings.get_value("role_staff")), read_messages=True)
        await channel.set_permissions(ctx.author, read_messages=True)

        # If the ticket creator is a VIP, ping the staff for fast response.
        if any(role.id == settings.get_value("role_vip") for role in ctx.author.roles):
            await channel.send(f"<@&{settings.get_value('role_staff')}>")

        # Create an embed at the top of the new ticket so the mod knows who opened it.
        embed = embeds.make_embed(
            title="🎫  Ticket created",
            description="Please remain patient for a staff member to assist you.",
            color="default"
        )
        embed.add_field(name="Ticket Creator:", value=ctx.author.mention, inline=False)
        embed.add_field(name="Ticket Topic:", value=topic, inline=False)
        await channel.send(embed=embed)

        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        # Insert a pending ticket into the database.
        db["tickets"].insert(dict(
            user_id=ctx.author.id,
            status="in-progress",
            guild=ctx.guild.id,
            timestamp=int(time.time()),
            ticket_topic=topic,
            log_url=None
        ))

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

        # Send the user a ping and then immediately delete it because mentions via embeds do not ping.
        ping = await channel.send(ctx.author.mention)
        await ping.delete()

        embed = embeds.make_embed(ctx=ctx, title="Created a ticket", description=f"Opened a ticket: {channel.mention} for: {topic}.")
        await ctx.send(embed=embed, hidden=True)

    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="close",
        description="Closes a ticket when sent in the ticket channel",
        guild_ids=[settings.get_value("guild_id")],
        default_permission=False,
        permissions={
            settings.get_value("guild_id"): [
                create_permission(settings.get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
                create_permission(settings.get_value("role_trial_mod"), SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def close(self, ctx: SlashContext):
        """ Closes the modmail ticket."""
        # Needed for commands that take longer than 3 seconds to respond to avoid "This interaction failed".
        await ctx.defer()

        # Warns if the ticket close command is called outside of the current active ticket channel.
        if not ctx.channel.category_id == settings.get_value('category_tickets') or "ticket" not in ctx.channel.name:
            await embeds.error_message(ctx=ctx, description="You can only run this command in active ticket channels.")
            return

        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        # Get the ticket in the database.
        table = db["tickets"]
        ticket = table.find_one(user_id=int(ctx.channel.name.replace("ticket-", "")), status="in-progress")

        # If the ticket exists in the database.
        if ticket:
            # Get the ticket topic from database and ticket creator's ID from channel name.
            ticket_topic = ticket["ticket_topic"]
            ticket_creator_id = int(ctx.channel.name.replace("ticket-", ""))
        # If somehow the ticket doesn't exist in the database.
        else:
            # Attempts to get only the first embedded message by Chiya in the ticket channel.
            async for message in ctx.channel.history(oldest_first=True):
                # If the message author's ID is the same as Chiya.
                if message.author.id == self.bot.user.id:
                    # There should be only 1 embed in the message, so we get the first item.
                    # The first field's value is guaranteed to be the ticket creator. We strip the non-digit chars and turn the rest into an int.
                    ticket_creator_id = int(re.sub(r"\D+", "", message.embeds[0].fields[0].value))
                    # The second field's value is guaranteed to be the ticket topic.
                    ticket_topic = message.embeds[0].fields[1].value
                    break

        # Get the member object of the ticket creator.
        member = await self.bot.fetch_user(ticket_creator_id)

        # Initialize the PrivateBin message log string.
        message_log = (
            f"Ticket Creator: {member}\n"
            f"User ID: {member.id}\n"
            f"Ticket Topic: {ticket_topic}\n\n"
        )

        # Initialize a list of moderator IDs as a set for no duplicates.
        mod_list = set()

        # Fetch the staff and trial mod role.
        role_staff = discord.utils.get(ctx.guild.roles, id=settings.get_value("role_staff"))
        role_trial_mod = discord.utils.get(ctx.guild.roles, id=settings.get_value("role_trial_mod"))

        # Loop through all messages in the ticket from old to new.
        async for message in ctx.channel.history(oldest_first=True):
            # Ignore the bot replies.
            if not message.author.bot:

                # Time format is unnecessarily lengthy so trimming it down and keep the log go easier on the eyes.
                formatted_time = str(message.created_at).split(".")[-2]

                # Append the new messages to the current log as we loop.
                message_log += f"[{formatted_time}] {message.author}: {message.content}\n"

                # If the messenger has either staff role or trial mod role, add their ID to the mod_list set.
                if role_staff in message.author.roles or role_trial_mod in message.author.roles:
                    mod_list.add(message.author)

        # An empty mod_list (ticket with no conversation) will raise a HTTPException for using an empty field in embed.
        # Using "\u200b" (zero width space) is also not an option because .mention cannot be called on it.
        if len(mod_list) == 0:
            mod_list.add(self.bot.user)

        # Dump message log to PrivateBin. This returns a dictionary, but only the url is needed for the embed.
        url = privatebinapi.send("https://bin.piracy.moe", text=message_log, expiration="never")["full_url"]

        # Create the embed in #ticket-log.
        embed = embeds.make_embed(
            ctx=ctx,
            author=False,
            title=f"{ctx.channel.name} archived",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color=0x00ffdf
        )

        embed.add_field(name="Ticket Creator:", value=member.mention, inline=True)
        embed.add_field(name="Closed By:", value=ctx.author.mention, inline=True)
        embed.add_field(name="Ticket Topic:", value=ticket_topic, inline=False)
        embed.add_field(name="Participating Moderators:", value=" ".join(mod.mention for mod in mod_list), inline=False)
        embed.add_field(name="Ticket Log: ", value=url, inline=False)

        # Send the embed to #ticket-log.
        ticket_log = discord.utils.get(ctx.guild.channels, id=settings.get_value("channel_ticket_log"))
        await ticket_log.send(embed=embed)

        # DM the user that their ticket was closed.
        try:
            embed = embeds.make_embed(
                author=False,
                color=0xf4cdc5,
                title=f"Ticket closed",
                description="Your ticket was closed. Please feel free to create a new ticket should you have any further inquiries.",
            )
            embed.add_field(name="Server:", value=f"[{ctx.guild}](https://discord.gg/piracy/)", inline=False)
            embed.add_field(name="Ticket Log:", value=url, inline=False)
            embed.set_image(url="https://i.imgur.com/21nJqGC.gif")
            await member.send(embed=embed)
        except discord.HTTPException:
            logging.info(f"Attempted to send ticket closed DM to {member} but they are not accepting DMs.")

        # If the ticket somehow does not exists in the database, we add it.
        if not ticket:
            db["tickets"].insert(dict(
                user_id=ticket_creator_id,
                status="completed",
                guild=ctx.guild.id,
                timestamp=int(time.time()),
                ticket_topic=ticket_topic,
                log_url=url
            ))
        else:
            # Otherwise, update the ticket status from "in-progress" to "completed" and the PrivateBin URL field in the database.
            ticket["status"] = "completed"
            ticket["log_url"] = url
            table.update(ticket, ["id"])

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

        # Delete the channel.
        await ctx.channel.delete()


def setup(bot: Bot) -> None:
    """ Load the Ticket cog. """
    bot.add_cog(TicketCog(bot))
    log.info("Commands loaded: tickets")
