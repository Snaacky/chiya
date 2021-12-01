import logging
import time

import discord
import privatebinapi
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext, ComponentContext
from discord_slash.model import SlashCommandPermissionType, ButtonStyle
from discord_slash.utils.manage_commands import create_option, create_permission
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component

from utils import database, embeds
from utils.config import config


log = logging.getLogger(__name__)


class TicketCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="ticket",
        description="Opens a new modmail ticket",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="topic",
                description="A brief summary of the topic you would like to discuss",
                option_type=3,
                required=True,
            )
        ],
    )
    async def open(self, ctx: SlashContext, topic: str):
        """Opens a new modmail ticket."""
        await ctx.defer(hidden=True)

        if len(topic) > 1024:
            return await ctx.send(
                embed=embeds.error_message(
                    description=(
                        "Your ticket topic exceeded 1024 characters. "
                        "Please keep the topic concise and further elaborate it in the ticket instead."
                    )
                ),
                hidden=True
            )

        category = discord.utils.get(ctx.guild.categories, id=config["categories"]["tickets"])
        ticket = discord.utils.get(category.text_channels, name=f"ticket-{ctx.author.id}")

        if ticket:
            logging.info(f"{ctx.author} tried to create a new ticket but already had one open: {ticket}")
            return await ctx.send(f"You already have a ticket open! {ticket.mention}", hidden=True)

        permissions = {
            discord.utils.get(ctx.guild.roles, id=config["roles"]["trial_mod"]): discord.PermissionOverwrite(read_messages=True),
            discord.utils.get(ctx.guild.roles, id=config["roles"]["staff"]): discord.PermissionOverwrite(read_messages=True),
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True),
        }

        channel = await ctx.guild.create_text_channel(
            name=f"ticket-{ctx.author.id}",
            category=category,
            overwrites=permissions,
            topic=topic,
        )

        if any(role.id == config["roles"]["vip"] for role in ctx.author.roles):
            await channel.send(f"<@&{config['roles']['staff']}>")

        embed = embeds.make_embed(
            title="🎫  Ticket created",
            description="Please remain patient for a staff member to assist you.",
            color="default",
        )
        embed.add_field(name="Ticket Creator:", value=ctx.author.mention, inline=False)
        embed.add_field(name="Ticket Topic:", value=topic, inline=False)
        await channel.send(embed=embed)

        db = database.Database().get()
        db["tickets"].insert(dict(
            user_id=ctx.author.id,
            status="in-progress",
            guild=ctx.guild.id,
            timestamp=int(time.time()),
            ticket_topic=topic,
            log_url=None,
        ))
        db.commit()
        db.close()

        # Send the user a ping and then immediately delete it because mentions via embeds do not ping.
        ping = await channel.send(ctx.author.mention)
        await ping.delete()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Created a ticket",
            description=f"Opened a ticket: {channel.mention} for: {topic}.",
        )
        await ctx.send(embed=embed, hidden=True)

    @cog_ext.cog_slash(
        name="close",
        description="Closes a ticket when sent in the ticket channel",
        guild_ids=[config["guild_id"]],
        default_permission=False,
        permissions={
            config["guild_id"]: [
                create_permission(
                    config["roles"]["staff"],
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
                create_permission(
                    config["roles"]["trial_mod"],
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
            ]
        },
    )
    async def close(self, ctx: SlashContext):
        """Closes the modmail ticket."""
        # Needed for commands that take longer than 3 seconds to respond to avoid "This interaction failed".
        await ctx.defer()

        # Warns if the ticket close command is called outside of the current active ticket channel.
        if not ctx.channel.category_id == config["categories"]["tickets"] or "ticket" not in ctx.channel.name:
            return await embeds.error_message(
                ctx=ctx,
                description="You can only run this command in active ticket channels.",
            )

        db = database.Database().get()
        table = db["tickets"]
        ticket = table.find_one(user_id=int(ctx.channel.name.replace("ticket-", "")), status="in-progress")

        # Get the ticket topic and ticket creator's ID from channel name.
        ticket_creator_id = int(ctx.channel.name.replace("ticket-", ""))
        ticket_topic = ctx.channel.topic

        # Get the member object of the ticket creator.
        member = await self.bot.fetch_user(ticket_creator_id)

        # Initialize the PrivateBin message log string.
        message_log = f"Ticket Creator: {member}\n" f"User ID: {member.id}\n" f"Ticket Topic: {ticket_topic}\n\n"

        # Initialize a list of moderator IDs as a set for no duplicates.
        mod_list = set()

        # Fetch the staff and trial mod role.
        role_staff = discord.utils.get(ctx.guild.roles, id=config["roles"]["staff"])
        role_trial_mod = discord.utils.get(ctx.guild.roles, id=config["roles"]["trial_mod"])

        # Loop through all messages in the ticket from old to new.
        async for message in ctx.channel.history(oldest_first=True):
            # Ignore the bot replies.
            if not message.author.bot:
                # Pretty print the time tag into a more digestible format.
                formatted_time = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                # Append the new messages to the current log as we loop.
                message_log += f"[{formatted_time}] {message.author}: {message.content}\n"
                # Iterates only through members that is still in the server.
                if isinstance(message.author, discord.Member):
                    # If the messenger has either staff role or trial mod role, add their ID to the mod_list set.
                    if role_staff in message.author.roles or role_trial_mod in message.author.roles:
                        mod_list.add(message.author)

        # An empty embed field will raise an HTTPException.
        if len(mod_list) == 0:
            mod_list.add(self.bot.user)

        # Gets the paste URL from the PrivateBin POST.
        url = privatebinapi.send(config["privatebin"]["url"], text=message_log, expiration="never")["full_url"]

        # Create the embed in #ticket-log.
        embed = embeds.make_embed(
            ctx=ctx,
            author=False,
            title=f"{ctx.channel.name} archived",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color=0x00FFDF,
        )

        embed.add_field(name="Ticket Creator:", value=member.mention, inline=True)
        embed.add_field(name="Closed By:", value=ctx.author.mention, inline=True)
        embed.add_field(name="Ticket Topic:", value=ticket_topic, inline=False)
        embed.add_field(
            name="Participating Moderators:",
            value=" ".join(mod.mention for mod in mod_list),
            inline=False,
        )
        embed.add_field(name="Ticket Log: ", value=url, inline=False)

        # Send the embed to #ticket-log.
        ticket_log = discord.utils.get(ctx.guild.channels, id=config["channels"]["ticket_log"])
        await ticket_log.send(embed=embed)

        # DM the user that their ticket was closed.
        try:
            embed = embeds.make_embed(
                author=False,
                color=0xF4CDC5,
                title="Ticket closed",
                description=(
                    "Your ticket was closed. "
                    "Please feel free to create a new ticket should you have any further inquiries."
                )
            )
            embed.add_field(
                name="Server:",
                value=f"[{ctx.guild}](https://discord.gg/piracy)",
                inline=False,
            )
            embed.add_field(name="Ticket Log:", value=url, inline=False)
            embed.set_image(url="https://i.imgur.com/21nJqGC.gif")
            await member.send(embed=embed)
        except discord.HTTPException:
            logging.info(f"Attempted to send ticket log DM to {member} but they are not accepting DMs.")

        ticket["status"] = "completed"
        ticket["log_url"] = url
        table.update(ticket, ["id"])

        db.commit()
        db.close()

        # Delete the channel.
        await ctx.channel.delete()


def setup(bot: Bot) -> None:
    bot.add_cog(TicketCog(bot))
    log.info("Commands loaded: tickets")
