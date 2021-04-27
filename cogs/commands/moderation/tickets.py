import asyncio
import logging

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, Greedy

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

    @commands.has_role(config.role_staff)
    @commands.before_invoke(record_usage)
    @commands.group()
    async def ticket(self, ctx):
        if ctx.invoked_subcommand is None:
            # Send the help command for this group
            await ctx.send_help(ctx.command)

    @commands.has_role(config.role_staff)
    @commands.before_invoke(record_usage)
    @ticket.command(name="close")
    async def close(self, ctx):
        """ Closes the modmail ticket."""
        channel = ctx.message.channel

        if not channel.category_id == config.ticket_category_id or "ticket" not in channel.name:
            embed = embeds.make_embed(color=config.soft_red)
            embed.description=f"You can only run this command in active ticket channels."
            await ctx.reply(embed=embed)
            return

        # Send notice that the channel has been marked read only and will be archived.
        embed = embeds.make_embed(author=False, color=0xffffc3)
        embed.title = f"🔒 Your ticket has been closed."
        embed.description = f"The channel has been marked read-only and will be archived in one minute. If you have additional comments or concerns, feel free to open another ticket."
        embed.set_image(url="https://i.imgur.com/TodlFQq.gif")
        await ctx.send(embed=embed)

        # Set the channel into a read only state.
        for role in channel.overwrites:
            # default_role is @everyone role, so skip that.
            if role == ctx.guild.default_role:
                continue
            await channel.set_permissions(role, read_messages=True, send_messages=False, add_reactions=False, manage_messages=False)     

        with dataset.connect(database.get_db()) as db:
            table = db["tickets"]
            ticket = table.find_one(user_id=int(ctx.channel.name.replace("ticket-", "")), status=1)
            ticket["status"] = 2
            table.update(ticket, ["id"])           

        # Sleep for 60 seconds before archiving the channel.
        await asyncio.sleep(60)

        # Move the channel to the archive.
        archive = discord.utils.get(ctx.guild.categories, id=config.archive_category)
        await ctx.channel.edit(category=archive, sync_permissions=True)

def setup(bot: Bot) -> None:
    """ Load the Ticket cog. """
    bot.add_cog(TicketCog(bot))
    log.info("Commands loaded: tickets")
