import logging
import time

import dataset
import discord
from discord.ext import commands

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
            logging.info(f"{member} tried to create a new ticket but already had one open: {ticket} and was unable to DM them.")
            return

        # If we didn't hit any of the above, assume we were able to successfully DM the user about their duplicate ticket.
        logging.info(f"{member} tried to create a new ticket but already had one open: {ticket}")
        return

    # Check if a pending ticket already exists for the member.
    ticket = await check_for_pending_tickets(member)
    if ticket:
        # If one exists, log but do nothing because the latest embed is still awaiting their response.
        logging.info(f"{member} tried to create a new ticket but already had one pending")
        return

    # Send the user the pending ticket DM embed.
    dm = await send_pending_ticket_dm(member)

    # Insert a pending ticket into the database.
    with dataset.connect(database.get_db()) as db:
        db["tickets"].insert(dict(
            user_id=member.id, status=0, guild=payload.guild_id, ticket_channel=None, 
            dm_embed_id=dm.id, timestamp=int(time.time())
        ))
    


async def process_pending_ticket(bot, message):
    with dataset.connect(database.get_db()) as db:
        table = db["tickets"]

    ticket = table.find_one(user_id=message.author.id, status=0)
    if not ticket:
        return

    channel = await create_ticket_channel(bot, ticket, message)
    logging.info(f"{message.author} created a new modmail ticket: {channel.id}")
    
    ticket["status"] = 1
    ticket["ticket_channel"] = channel.id
    table.update(ticket, ["id"])


async def process_dm_reaction(bot, payload):
    # Get the member object for the user who added the reaction.
    user = await bot.fetch_user(payload.user_id)

    with dataset.connect(database.get_db()) as db:
        table = db["tickets"]
    
    ticket = table.find_one(dm_embed_id=payload.message_id)

    # If we did not find a ticket, we don't care what the user reacted to in DMs.
    if not ticket:
        return

    # Update the status of the ticket in the database.
    ticket["status"] = 3
    table.update(ticket, ["id"])
    logging.info(f"{user} canceled their pending ticket")
    
    # just doing things a bit more explicitly
    dm = await user.create_dm()
    await dm.send("canceled")

    # TODO: Send canceled ticket embed


async def check_for_duplicate_tickets(member):
    # Search for a pending ticket by iterating the tickets category for a match.
    ticket = discord.utils.get(discord.utils.get(member.guild.categories, 
                                id=config.ticket_category_id).text_channels, 
                                name=f"ticket-{member.id}")
    
    # If ticket returned no results, no duplicate tickets were found.
    if not ticket:
        return False

    # If we hit this point, a duplicate ticket was found.
    return ticket


async def check_for_pending_tickets(member):
    # Open a connection the database.
    with dataset.connect(database.get_db()) as db:
        table = db["tickets"]

    # Search for any pending tickets in the database.
    ticket = table.find_one(user_id=member.id, status=0)
    
    # If ticket returned no results, no pending tickets were found.
    if not ticket:
        return False

    # If we hit this point, a pending ticket was found.
    return ticket


async def send_pending_ticket_dm(member):
    try:
        dm = await member.create_dm()
        embed = embeds.make_embed(author=False, color=0xd0c68d)
        embed.title = f"Ticket creation"
        embed.description = "To submit your ticket, please respond below with a brief description of why you're contacting us. \n\nIf you did not mean to create a ticket, you can react to the <:no:778724416230129705> below to cancel the ticket."
        embed.set_image(url="https://i.imgur.com/D8xrxnD.gif")
        msg = await dm.send(embed=embed)
        await msg.add_reaction(":no:778724416230129705")
        return msg
    except discord.errors.Forbidden:
        logging.info(f"{member} tried to create a new pending ticket but is not accepting DMs.")


async def send_duplicate_ticket_dm(member, ticket):
    try:
        dm = await member.create_dm()
        embed = embeds.make_embed(author=False, color=0xf999de)
        embed.title = f"Uh-oh, an error occurred!"
        embed.description = f"You attempted to create a new ticket but you already have one open. Please refer to {ticket.mention} for assistance."
        embed.set_image(url="https://i.imgur.com/VTqz1oS.gif")
        await dm.send(embed=embed)
        return True
    except discord.errors.Forbidden:
        # Could not DM the user because they don't accept DMs.
        logging.info(f"{member} tried to create a new ticket but already had one open: {ticket} and is not accepting DMs.")
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

    # Create an embed at the top of the new ticket so the mod knows who opened it.
    embed = embeds.make_embed(title="🎫  Ticket created", 
                                description="Please remain patient for a staff member to assist you.", 
                                color="default")
    embed.add_field(name="Ticket Creator:", value=member.mention, inline=False)
    embed.add_field(name="Ticket Topic:", value=message.content, inline=False)
    await ticket.send(embed=embed)
    
    return ticket