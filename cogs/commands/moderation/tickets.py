import logging

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_permission
from discord_slash.model import SlashCommandPermissionType
import privatebinapi

import config
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
    @cog_ext.cog_subcommand(
        base="ticket",
        name="close",
        description="Closes an active ticket",
        guild_ids=[config.guild_id],
        base_default_permission=False,
        base_permissions={
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
                create_permission(config.role_trial_mod, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def close(self, ctx: SlashContext):
        """ Closes the modmail ticket."""
        # Warns if the ticket close command is called outside of the current active ticket channel.
        if not ctx.channel.category_id == config.ticket_category_id or "ticket" not in ctx.channel.name:
            await embeds.error_message(ctx=ctx, description="You can only run this command in active ticket channels.")
            return

        # Get the ticket topic in database for embeds.
        with dataset.connect(database.get_db()) as db:
            table = db["tickets"]
            ticket = table.find_one(user_id=int(ctx.channel.name.replace("ticket-", "")), status="in-progress")
            ticket_topic = ticket["ticket_topic"]

        # Needed for commands that take longer than 3 seconds to respond to avoid "This interaction failed".
        await ctx.defer()

        # Get the member object of the ticket creator.
        member = await ctx.guild.fetch_member(int(ctx.channel.name.replace("ticket-", "")))

        # Initialize the PrivateBin message log string.
        message_log = f"Ticket Creator: {member}\nUser ID: {member.id}\nTicket Topic: {ticket_topic}\n\n"

        # Initialize a list of moderator IDs as a set for no duplicates.
        mod_list = set()

        # Add the closing mod just in case no other mod interacts with the ticket to avoid an empty embed field.
        mod_list.add(ctx.author)

        # Fetch the staff and trial mod role.
        role_staff = discord.utils.get(ctx.guild.roles, id=config.role_staff)
        role_trial_mod = discord.utils.get(ctx.guild.roles, id=config.role_trial_mod)

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

        # Dump message log to PrivateBin. This returns a dictionary, but only the url is needed for the embed.
        url = privatebinapi.send("https://bin.piracy.moe", text=message_log, expiration="never")["full_url"]

        # Create the embed in #ticket-log.
        embed = embeds.make_embed(
            ctx=ctx,
            author=False,
            title=f"{ctx.channel.name} archived",
            thumbnail_url=config.pencil,
            color=0x00ffdf
        )

        embed.add_field(name="Ticket Creator:", value=member.mention, inline=False)
        embed.add_field(name="Ticket Topic:", value=ticket_topic, inline=False)
        embed.add_field(name="Participating Moderators:", value=" ".join(mod.mention for mod in mod_list), inline=False)
        embed.add_field(name="Ticket Log: ", value=url, inline=False)

        # Send the embed to #ticket-log.
        ticket_log = discord.utils.get(ctx.guild.channels, id=config.ticket_log)
        await ticket_log.send(embed=embed)

        # DM the user that their ticket was closed.
        try:
            embed = embeds.make_embed(
                author=False, 
                color=0xf4cdc5,
                title=f"Ticket closed",
                description="Your ticket was closed. Please feel free to create a new ticket should you have any further inquiries.",
                image_url="https://i.imgur.com/21nJqGC.gif"
            )
            embed.add_field(name="Ticket log:", value=url)

            await member.send(embed=embed)
        except discord.HTTPException:
            logging.info(f"Attempted to send ticket closed DM to {member} but they are not accepting DMs.")

        # Update the ticket status from "in-progress" to "completed" and the PrivateBin URL field in the database.
        ticket["status"] = "completed"
        ticket["log_url"] = url
        table.update(ticket, ["id"])

        # Delete the channel.
        await ctx.channel.delete()


def setup(bot: Bot) -> None:
    """ Load the Ticket cog. """
    bot.add_cog(TicketCog(bot))
    log.info("Commands loaded: tickets")
