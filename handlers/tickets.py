import logging

import discord

import config
from utils import embeds


async def process_new_tickets(payload):
    # Get the member object for the user who added the reaction.
    member = payload.member.guild.get_member(payload.member.id)

    # Remove the users reaction to the creation embed.
    channel = discord.utils.get(member.guild.channels, id=config.ticket_channel)
    embed = await channel.fetch_message(config.ticket_embed_id)
    await embed.remove_reaction("🎫", member)

    # Check if a duplicate ticket already exists for the member.
    ticket = await check_for_duplicate_tickets(member)
    if ticket:
        logging.info(f"{member} tried to create a new ticket but already had one open: {ticket}")
        return

    # Create a new ticket channel.
    channel = await create_ticket_channel(payload, member)
    logging.info(f"{member} created a new modmail ticket: {channel.id}")


async def check_for_duplicate_tickets(member):
    # Check if the user already has a ticket open.  
    ticket = discord.utils.get(discord.utils.get(member.guild.categories, 
                                id=config.ticket_category_id).text_channels, 
                                name=f"ticket-{member.id}")

    # User already had a ticket open, send them a DM with a link to the existing ticket.
    if ticket:
        try:
            # Try/catch required because some users have DMs turned off.
            dm = await member.create_dm()
            embed = embeds.make_embed(author=False, color=0xf999de)
            embed.title = f"Uh-oh, an error occurred!"
            embed.description = f"You attempted to create a new ticket but you already have one open. Please refer to {ticket.mention} for assistance."
            embed.set_image(url="https://i.imgur.com/VTqz1oS.gif")
            await dm.send(embed=embed)
        except discord.errors.Forbidden:
            # Could not DM the user because they don't accept DMs.
            logging.info(f"{member} tried to create a new ticket but already had one open: {ticket} and is not accepting DMs.")
        return ticket
    return False


async def create_ticket_channel(payload, member):
    # Create a channel in the desired tickets category according to the config.
    category = discord.utils.get(member.guild.categories, id=config.ticket_category_id)        
    ticket = await member.guild.create_text_channel(f"ticket-{member.id}", category=category)

    # Give both the staff and the user perms to access the channel. 
    await ticket.set_permissions(discord.utils.get(member.guild.roles, id=config.role_trial_mod), read_messages=True)
    await ticket.set_permissions(discord.utils.get(member.guild.roles, id=config.role_staff), read_messages=True)
    await ticket.set_permissions(member.guild.get_member(member.id), read_messages=True)

    # Create an embed at the top of the new ticket so the mod knows who opened it.
    embed = embeds.make_embed(title="🎫  Ticket created", 
                                description="Please remain patient for a staff member to assist you.", 
                                color="default")
    embed.add_field(name="Ticket Creator:", value=member.mention)
    await ticket.send(embed=embed)
    
    return ticket