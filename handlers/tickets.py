import logging
import time

import dataset
import discord

import config
from utils import database
from utils import embeds


async def process_embed_reaction(payload):
    # Get the member object for the user who added the reaction.
    member = await payload.member.guild.fetch_member(payload.member.id)

    # Remove the users reaction to the creation embed.
    channel = discord.utils.get(member.guild.channels, id=config.ticket_channel)
    embed = await channel.fetch_message(config.ticket_embed_id)
    await embed.remove_reaction("🎫", member)

    # Check if a duplicate ticket already exists for the member.
    ticket = await check_for_duplicate_tickets(member)

    if ticket:
        # Attempt to send the user a DM telling them that they already have a ticket open.
        results = await send_duplicate_ticket_dm(member, ticket)

        # If results returns False, we were unable to DM the user because they're not accepting DMs.
        if not results:
            logging.info(f"{member} tried to create a new ticket but already had one open: {ticket} and was unable to DM them")
            return

        # If we didn't hit any of the above, assume we were able to successfully DM the user about their duplicate ticket.
        logging.info(f"{member} tried to create a new ticket but already had one open: {ticket}")
        return

    # Check if a pending ticket already exists for the member.
    ticket = await check_for_pending_tickets(member)

    # If one exists, log but do nothing because the latest embed is still awaiting their response.
    if ticket:
        logging.info(f"{member} tried to create a new ticket but already had one pending")
        return

    # Send the user the pending ticket DM embed.
    dm = await send_pending_ticket_dm(member)

    # Insert a pending ticket into the database.
    with dataset.connect(database.get_db()) as db:
        db["tickets"].insert(dict(
            user_id=member.id, status="pending", guild=payload.guild_id,
            dm_embed_id=dm.id, timestamp=int(time.time()), ticket_topic=None, log_url=None
        ))


async def process_pending_ticket(bot, message):
    # Open a connection to the database.
    with dataset.connect(database.get_db()) as db:
        table = db["tickets"]

    # Check if the user has any currently pending tickets.
    ticket = table.find_one(user_id=message.author.id, status="pending")
    if not ticket:
        return

    # Update the ticket in the database from "pending" to "in-progress", and store the channel ID and ticket topic.
    ticket["status"] = "in-progress"
    ticket["ticket_topic"] = message.content
    table.update(ticket, ["id"])

    # If the user does not have any pending tickets, create a new ticket channel.
    channel = await create_ticket_channel(bot, ticket, message)
    logging.info(f"{message.author} created a new modmail ticket: {channel.id}")

    # Send the user a DM with a link to their ticket so they know it was successfully created.
    embed = embeds.make_embed(author=False, color=0xd56385)
    embed.title = f"Ticket created"
    embed.add_field(name="Topic:", value=message.content, inline=False)
    embed.add_field(name="Ticket:", value=channel.mention, inline=False)
    embed.set_image(url="https://i.imgur.com/YiIfTLc.gif")
    await message.author.send(embed=embed)


async def process_dm_reaction(bot, payload):
    # Get the member object for the user who added the reaction.
    user = await bot.fetch_user(payload.user_id)

    # checking if the reaction is from the bot itself
    if user == bot.user:
        return

    # Search the database for an open pending ticket.
    with dataset.connect(database.get_db()) as db:
        table = db["tickets"]

    ticket = table.find_one(dm_embed_id=payload.message_id, status="pending")

    # If we did not find a ticket, ignore the reaction.
    if not ticket:
        return

    # Update the status of the ticket in the database to "canceled".
    ticket["status"] = "canceled"
    table.update(ticket, ["id"])
    logging.info(f"{user} canceled their pending ticket")

    # DM the user an embed stating that their ticket was successfully canceled.
    embed = embeds.make_embed(author=False, color=0xf4cdc5)
    embed.title = f"Ticket canceled"
    embed.description = "Aw... feel free to create a new ticket if you need anything..."
    embed.set_image(url="https://i.imgur.com/T9ikYl6.gif")
    await user.send(embed=embed)


async def check_for_duplicate_tickets(member):
    # Search for a pending ticket by iterating the tickets category for a channel name match.
    ticket = discord.utils.get(discord.utils.get(member.guild.categories,
                               id=config.ticket_category_id).text_channels,
                               name=f"ticket-{member.id}")

    # If ticket returned no results, no duplicate tickets were found.
    if not ticket:
        return False

    # If we hit this point, a duplicate ticket was found.
    return ticket


async def check_for_pending_tickets(member):
    # Open a connection to the database.
    with dataset.connect(database.get_db()) as db:
        table = db["tickets"]

    # Search for any pending tickets in the database.
    ticket = table.find_one(user_id=member.id, status="pending")

    # If ticket returned no results, no pending tickets were found.
    if not ticket:
        return False

    # If we hit this point, a pending ticket was found.
    return ticket


async def send_pending_ticket_dm(member):
    # Attempt to open a new DM with user so we can get the ticket topic.
    try:
        dm = await member.create_dm()
        embed = embeds.make_embed(author=False, color=0xd0c68d)
        embed.title = f"Ticket creation"
        embed.description = "To submit your ticket, please respond below with a brief description of why you're contacting us. \n\nIf you did not mean to create a ticket, you can react to the <:no:778724416230129705> below to cancel the ticket."
        embed.set_image(url="https://i.imgur.com/D8xrxnD.gif")
        msg = await dm.send(embed=embed)
        await msg.add_reaction(":no:778724416230129705")
        return msg
    # If the user is not accepting DMs, we'll hit a forbidden exception.
    except discord.errors.Forbidden:
        logging.info(f"{member} tried to create a new pending ticket but is not accepting DMs.")


async def send_duplicate_ticket_dm(member, ticket):
    # Attempts to create a new DM with the user for the topic. 
    try:
        dm = await member.create_dm()
        embed = embeds.make_embed(author=False, color=0xf999de)
        embed.title = f"Uh-oh, an error occurred!"
        embed.description = f"You attempted to create a new ticket but you already have one open. Please refer to {ticket.mention} for assistance."
        embed.set_image(url="https://i.imgur.com/VTqz1oS.gif")
        await dm.send(embed=embed)
        return True
    # If the user has DMs disabled, we'll receive a forbidden exception.
    except discord.errors.Forbidden:
        logging.info(f"{member} tried to create a new ticket but already had one open: {ticket} and is not accepting DMs")
    return False


async def create_ticket_channel(bot, ticket, message):
    guild = bot.get_guild(ticket["guild"])
    member = await guild.fetch_member(message.author.id)
    category = discord.utils.get(guild.categories, id=config.ticket_category_id)

    # Create a channel in the tickets category specified in the config.
    ticket = await member.guild.create_text_channel(f"ticket-{member.id}", category=category)

    # Give both the staff and the user perms to access the channel. 
    await ticket.set_permissions(discord.utils.get(guild.roles, id=config.role_trial_mod), read_messages=True)
    await ticket.set_permissions(discord.utils.get(guild.roles, id=config.role_staff), read_messages=True)
    await ticket.set_permissions(member, read_messages=True)

    # If the ticket creator is a VIP, ping the seniors and admins and restrict message permission to them.
    if any(role.id == config.role_vip for role in member.roles):
        await ticket.set_permissions(discord.utils.get(guild.roles, id=config.role_trial_mod), send_messages=False)
        await ticket.set_permissions(discord.utils.get(guild.roles, id=config.role_staff), send_messages=False)
        await ticket.set_permissions(discord.utils.get(guild.roles, id=config.role_senior_mod), send_messages=True)
        await ticket.send(f"<@&{config.role_admin}> <@&{config.role_senior_mod}>")

    # Create an embed at the top of the new ticket so the mod knows who opened it.
    embed = embeds.make_embed(title="🎫  Ticket created",
                              description="Please remain patient for a staff member to assist you.",
                              color="default")
    embed.add_field(name="Ticket Creator:", value=member.mention, inline=False)
    embed.add_field(name="Ticket Topic:", value=message.content, inline=False)
    await ticket.send(embed=embed)

    return ticket
