import logging
import time

import discord
import privatebinapi
from discord.commands import context, permissions, slash_command
from discord.ext import commands

from utils import database, embeds
from utils.config import config

log = logging.getLogger(__name__)


class TicketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """ Register the embed button and ticket close button that persists between bot restarts. """
        self.bot.add_view(TicketCreateButton())
        self.bot.add_view(TicketCloseButton())

    @slash_command(
        guild_ids=config["guild_ids"],
        description="Create the embed ticket",
        default_permission=False,
        permissions=[permissions.Permission(id=config["roles"]["staff"], type=1, permission=True)],
    )
    async def ticket(self, ctx: context.ApplicationContext) -> None:
        """
        Command to create an embed that allows creating tickets.

        Permission type 1 is role and type 2 is user.
        """
        await ctx.defer()

        embed = embeds.make_embed(
            title="📫  Open a ticket",
            description="To create a ticket, click on the button below.",
            footer="Abusing will result in a ban. Only use this feature for serious inquiries.",
            color=discord.Color.blurple(),
        )
        await ctx.send_followup(embed=embed, view=TicketCreateButton())


class TicketCreateButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket", emoji="✉")
    async def create_ticket(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """
        The create ticket button of the ticket embed, that prompts for confirmation before proceeding.

        The `button` parameter is positional and required despite unused.
        """
        embed = embeds.make_embed(
            description=f"{interaction.user.mention}, are you sure that you want to open a ticket?",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, view=TicketConfirmButtons(), ephemeral=True)


class TicketConfirmButtons(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.primary, custom_id="confirm_ticket")
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """
        The confirm button to open a ticket. Return if the user already have a ticket opened. Otherwise,
        create a private ticket channel, ghost ping the author and ping staff if the author is a VIP,
        send a pinned embed with a close button, and create a pending ticket entry in the database.

        The `button` parameter is positional and required despite unused.
        """
        category = discord.utils.get(interaction.guild.categories, id=config["categories"]["tickets"])
        ticket = discord.utils.get(category.text_channels, name=f"ticket-{interaction.user.id}")

        if ticket:
            embed = embeds.make_embed(
                color=discord.Color.blurple(),
                description=f"{interaction.user.mention}, you already have a ticket open at: {ticket.mention}"
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        role_staff = discord.utils.get(interaction.guild.roles, id=config["roles"]["staff"])
        permission = {
            role_staff: discord.PermissionOverwrite(read_messages=True),
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
        }

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            category=category,
            overwrites=permission,
        )

        if any(role.id == config["roles"]["vip"] for role in interaction.user.roles):
            await channel.send(f"<@&{config['roles']['staff']}>")

        embed = embeds.make_embed(
            title="🎫  Ticket created",
            description=(
                "Please wait patiently until a staff member is able to assist you. "
                "In the meantime, briefly describe what you need help with."
            ),
            fields=[{"name": "Ticket Creator:", "value": interaction.user.mention, "inline": False}],
            color=discord.Color.blurple(),
        )

        message = await channel.send(embed=embed, view=TicketCloseButton())
        await message.pin()

        ping = await channel.send(interaction.user.mention)
        await ping.delete()

        embed = embeds.make_embed(
            title="Created a ticket",
            description=f"Successfully opened a ticket: {channel.mention}",
            color=discord.Color.blurple(),
        )
        await interaction.response.edit_message(embed=embed, view=None)

        db = database.Database().get()
        db["tickets"].insert(dict(
            user_id=interaction.user.id,
            status="in-progress",
            guild=interaction.guild.id,
            timestamp=int(time.time()),
            log_url=None,
        ))

        db.commit()
        db.close()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_ticket")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """
        The cancel button to cancel the ticket creation attempt.

        The `button` parameter is positional and required despite unused.
        """
        embed = embeds.make_embed(color=discord.Color.red(), description="Your ticket creation request has been canceled.", )
        await interaction.response.edit_message(embed=embed, view=None)


class TicketCloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket", emoji="🔒")
    async def close(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """
        The close ticket button. Iterates through the channel's messages to create a log,
        send it to PrivateBin, send an embed into the log channel, and delete the channel.

        The `button` parameter is positional and required despite unused.
        """
        close_embed = embeds.make_embed(color=discord.Color.blurple(), description="The ticket will be closed shortly...")
        await interaction.response.send_message(embed=close_embed)

        db = database.Database().get()
        table = db["tickets"]
        ticket = table.find_one(user_id=int(interaction.channel.name.replace("ticket-", "")), status="in-progress")
        ticket_creator_id = int(interaction.channel.name.replace("ticket-", ""))
        member = discord.utils.get(interaction.guild.members, id=ticket_creator_id)
        role_staff = discord.utils.get(interaction.guild.roles, id=config["roles"]["staff"])
        role_trial_mod = discord.utils.get(interaction.guild.roles, id=config["roles"]["trial"])

        mod_list = set()
        message_log = f"Ticket Creator: {member}\nUser ID: {member.id}\n\n"

        async for message in interaction.channel.history(oldest_first=True, limit=None):
            if not message.author.bot:
                formatted_time = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                message_log += f"[{formatted_time}] {message.author}: {message.content}\n"
                # Check if ticket participant is still in the server and add to the mod_list if it's staff.
                if isinstance(message.author, discord.Member):
                    if role_staff in message.author.roles or role_trial_mod in message.author.roles:
                        mod_list.add(message.author)

        if len(mod_list) > 0:
            value = " ".join(mod.mention for mod in mod_list)
        else:
            value = mod_list.add("None")

        url = privatebinapi.send(config["privatebin"]["url"], text=message_log, expiration="never")["full_url"]

        log_embed = embeds.make_embed(
            title=f"{interaction.channel.name} archived",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color=discord.Color.blurple(),
            fields=[
                {"name": "Ticket Creator:", "value": member.mention, "inline": True},
                {"name": "Closed By:", "value": interaction.user.mention, "inline": True},
                {"name": "Participating Moderators:", "value": value, "inline": False},
                {"name": "Ticket Log:", "value": url, "inline": False},
            ])
        ticket_log = discord.utils.get(interaction.guild.channels, id=config["channels"]["logs"]["ticket_log"])
        await ticket_log.send(embed=log_embed)

        try:
            dm_embed = embeds.make_embed(
                image_url="https://i.imgur.com/21nJqGC.gif",
                color=discord.Color.blurple(),
                title="Ticket closed",
                description=(
                    "Your ticket was closed. "
                    "Please feel free to create a new ticket should you have any further inquiries."
                ),
                fields=[
                    {"name": "Server:", "value": f"[{interaction.guild.name}](https://discord.gg/piracy)", "inline": False},
                    {"name": "Ticket Log:", "value": url, "inline": False},
                ])
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            logging.info(f"Unable to send ticket log to {member} because their DM is closed")

        ticket["status"] = "completed"
        ticket["log_url"] = url
        table.update(ticket, ["id"])

        db.commit()
        db.close()

        await interaction.channel.delete()


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(TicketCommands(bot))
    log.info("Commands loaded: ticket")
