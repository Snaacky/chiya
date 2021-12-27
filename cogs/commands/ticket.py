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
    async def on_ready(self):
        """Register the embed button and ticket close button that persists between bot restarts."""
        self.bot.add_view(TicketCreateButton())
        self.bot.add_view(TicketCloseButton())

    @slash_command(
        guild_ids=config["guild_ids"],
        description="Create the embed ticket",
        default_permission=False,
        permissions=[permissions.Permission(id=config["roles"]["staff"], type=1, permission=True)],
    )
    async def ticket(self, ctx: context.ApplicationContext):
        """
        Create the ticket embed.

        Args:
            ctx (context.ApplicationContext): The context of the slash command.

        Notes:
            In the decorator, type 1 is role and type 2 is user.
        """
        await ctx.defer()

        embed = embeds.make_embed(
            color="blurple",
            title="📫  Open a ticket",
            description="To create a ticket, click on the button below.",
        )
        embed.set_footer(text="Abusing will result in a ban. Only use this feature for serious inquiries.")
        await ctx.respond(embed=embed, view=TicketCreateButton())


class TicketCreateButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket", emoji="✉")
    async def create_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        """
        The create ticket button of the ticket embed.

        Args:
            button (discord.ui.Button): Required positional argument that represents the button.
            interaction (discord.Interaction): The context of the interaction.
        """
        embed = embeds.make_embed(
            description=f"{interaction.user.mention}, are you sure that you want to open a ticket?",
            color="blurple",
        )
        await interaction.response.send_message(embed=embed, view=TicketConfirmButtons(), ephemeral=True)


class TicketConfirmButtons(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.primary, custom_id="confirm_ticket")
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        """
        The confirm button to open a ticket.

        Args:
            button (discord.ui.Button): Required positional argument that represents the button.
            interaction (discord.Interaction): The context of the interaction.
        """
        category = discord.utils.get(interaction.guild.categories, id=config["categories"]["tickets"])
        ticket = discord.utils.get(category.text_channels, name=f"ticket-{interaction.user.id}")

        if ticket:
            embed = embeds.make_embed(
                color="blurple",
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
            color="blurple",
            title="🎫  Ticket created",
            description="Please wait patiently until a staff member is able to assist you. In the meantime, briefly describe what you need help with.",
        )
        embed.add_field(name="Ticket Creator:", value=interaction.user.mention, inline=False)
        message = await channel.send(embed=embed, view=TicketCloseButton())
        await message.pin()

        ping = await channel.send(interaction.user.mention)
        await ping.delete()

        embed = embeds.make_embed(
            title="Created a ticket",
            description=f"Successfully opened a ticket: {channel.mention}",
            color="blurple",
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
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        """
        The cancel button to cancel the ticket creation attempt.

        Args:
            button (discord.ui.Button): Required positional argument that represents the button.
            interaction (discord.Interaction): The context of the interaction.
        """
        embed = embeds.make_embed(description="Your ticket creation request has been canceled.", color="soft_red")
        await interaction.response.edit_message(embed=embed, view=None)


class TicketCloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket", emoji="🔒")
    async def close(self, button: discord.ui.Button, interaction: discord.Interaction):
        """
        The close button to close and archive an existing ticket.

        Args:
            button (discord.ui.Button): Required positional argument that represents the button.
            interaction (discord.Interaction): The context of the interaction.
        """
        close_embed = embeds.make_embed(color="blurple", description="The ticket will be closed shortly...")
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
            author=False,
            title=f"{interaction.channel.name} archived",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color=0x00FFDF,
        )
        log_embed.add_field(name="Ticket Creator:", value=member.mention, inline=True)
        log_embed.add_field(name="Closed By:", value=interaction.user.mention, inline=True)
        log_embed.add_field(name="Participating Moderators:", value=value, inline=False)
        log_embed.add_field(name="Ticket Log: ", value=url, inline=False)
        ticket_log = discord.utils.get(interaction.guild.channels, id=config["channels"]["logs"]["ticket_log"])
        await ticket_log.send(embed=log_embed)

        try:
            embed = embeds.make_embed(
                author=False,
                color=0xF4CDC5,
                title="Ticket closed",
                description=(
                    "Your ticket was closed. "
                    "Please feel free to create a new ticket should you have any further inquiries."
                ),
            )
            embed.add_field(
                name="Server:",
                value=f"[{interaction.guild.name}](https://discord.gg/piracy)",
                inline=False,
            )
            embed.add_field(name="Ticket Log:", value=url, inline=False)
            embed.set_image(url="https://i.imgur.com/21nJqGC.gif")
            await member.send(embed=embed)
        except discord.HTTPException:
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
