import arrow
import discord
import privatebinapi
from discord.ext import commands
from loguru import logger
from sqlalchemy import select

from chiya import db
from chiya.config import config
from chiya.models import Ticket


class TicketCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """
        Register the embed button and ticket close button that persists
        between bot restarts.
        """
        self.bot.add_view(TicketCreateButton())
        self.bot.add_view(TicketCloseButton())

    @commands.is_owner()
    @commands.command(name="createticketembed")
    async def ticket(self, ctx: commands.Context) -> None:
        # TODO: Move this into the commands/administration.py cog.
        """
        Command to create an embed that allows creating tickets.
        """
        embed = discord.Embed()
        embed.title = "📫  Open a ticket"
        embed.description = "For serious inquiries, click the button below to create a ticket."
        embed.color = discord.Color.blurple()
        embed.set_footer(text="Any abuse of the ticket system will result in moderation action.")

        await ctx.send(embed=embed, view=TicketCreateButton())


class TicketSubmissionModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.TextInput(
                label="Subject:",
                placeholder="The subject of your ticket",
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            )
        )

        self.add_item(
            discord.ui.TextInput(
                label="Message:",
                placeholder="The message for your ticket",
                required=True,
                max_length=1024,
                style=discord.TextStyle.long,
            )
        )

    async def on_submit(self, ctx: discord.Interaction) -> None:
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not ctx or not ctx.guild:
            return

        category = discord.utils.get(ctx.guild.categories, id=config.categories.tickets)
        role_staff = discord.utils.get(ctx.guild.roles, id=config.roles.staff)
        permission = {
            role_staff: discord.PermissionOverwrite(read_messages=True),
            ctx.guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                manage_channels=False,
                manage_permissions=False,
                manage_messages=False,
            ),
            ctx.user: discord.PermissionOverwrite(read_messages=True),
        }

        channel = await ctx.guild.create_text_channel(
            name=f"ticket-{ctx.user.id}",
            category=category,
            overwrites=permission,
        )

        ticket_subject = self.children[0].value  # pyright: ignore[reportAttributeAccessIssue]
        ticket_message = self.children[1].value  # pyright: ignore[reportAttributeAccessIssue]

        embed = discord.Embed()
        embed.title = "🎫  Ticket created"
        embed.description = "Please wait patiently until a staff member is available to assist you."
        embed.color = discord.Color.blurple()
        embed.add_field(name="Ticket Creator:", value=ctx.user.mention, inline=False)
        embed.add_field(name="Ticket Subject:", value=ticket_subject, inline=False)
        embed.add_field(name="Ticket Message:", value=ticket_message, inline=False)

        message = await channel.send(embed=embed, view=TicketCloseButton())
        await message.pin()

        ping = await channel.send(ctx.user.mention)
        await ping.delete()

        embed = discord.Embed()
        embed.title = "Created a ticket"
        embed.description = f"Successfully opened a ticket: {channel.mention}"
        embed.color = discord.Color.blurple()

        await ctx.followup.send(embed=embed)

        ticket = Ticket()
        ticket.user_id = ctx.user.id
        ticket.guild = ctx.guild.id
        ticket.timestamp = arrow.utcnow().int_timestamp
        ticket.ticket_subject = ticket_subject
        ticket.ticket_message = ticket_message
        ticket.log_url = None
        ticket.status = False

        db.session.add(ticket)
        db.session.commit()


class TicketCreateButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket", emoji="✉")
    async def create_ticket(self, ctx: discord.Interaction, button: discord.ui.Button) -> None:
        """
        The create ticket button of the ticket embed, that prompts for
        confirmation before proceeding.

        The `button` parameter is positional and required despite unused.
        """
        category = discord.utils.get(ctx.guild.categories, id=config.categories.tickets)  # pyright: ignore[reportOptionalMemberAccess]
        ticket = discord.utils.get(category.text_channels, name=f"ticket-{ctx.user.id}")  # pyright: ignore[reportOptionalMemberAccess]

        if ticket:
            embed = discord.Embed()
            embed.title = "Error:"
            embed.description = f"{ctx.user.mention}, you already have a ticket open at: {ticket.mention}"
            embed.color = discord.Color.red()
            await ctx.response.send_message(embed=embed, ephemeral=True)

        modal = TicketSubmissionModal(title="Ticket Submission")
        await ctx.response.send_modal(modal)


class TicketCloseButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket", emoji="🔒")
    async def close(self, ctx: discord.Interaction, button: discord.ui.Button) -> None:
        """
        The close ticket button. Iterates through the channel's messages to
        create a log, send it to PrivateBin, send an embed into the log
        channel, and delete the channel.

        The `button` parameter is positional and required despite unused.
        """
        if not ctx.guild or not ctx.channel or not isinstance(ctx.channel, discord.TextChannel):
            return

        close_embed = discord.Embed()
        close_embed.color = discord.Color.blurple()
        close_embed.description = "This ticket will be archived and closed momentarily..."

        await ctx.response.send_message(embed=close_embed)

        user_id = int(ctx.channel.name.replace("ticket-", ""))  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
        ticket = db.session.scalar(select(Ticket).where(Ticket.user_id == user_id, Ticket.status.is_(False)))

        ticket_creator_id = int(ctx.channel.name.replace("ticket-", ""))
        ticket_subject = ticket.ticket_subject
        ticket_message = ticket.ticket_message

        role_staff = discord.utils.get(ctx.guild.roles, id=config.roles.staff)
        role_trial_mod = discord.utils.get(ctx.guild.roles, id=config.roles.trial)

        member = discord.utils.get(ctx.guild.members, id=ticket_creator_id)
        if not member:
            member = await ctx.client.fetch_user(ticket_creator_id)

        mod_list = set()
        mod_roles = (role_staff, role_trial_mod)
        message_log = f"Ticket Creator: {member}\nTicket Subject: {ticket_subject}\nTicket Message: {ticket_message}\nUser ID: {member.id}\n\n"

        async for message in ctx.channel.history(oldest_first=True, limit=None):
            if message.author.bot:
                continue

            formatted_time = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            message_log += f"[{formatted_time}] {message.author}: {message.content}\n"
            # Cannot do role check on participants who left the server (no role attribute).
            if isinstance(message.author, discord.Member) and any(role in mod_roles for role in message.author.roles):
                mod_list.add(message.author)

        value = " ".join(mod.mention for mod in mod_list) if mod_list else mod_list.add("None")
        url = privatebinapi.send(config.privatebin.url, text=message_log, expiration="never")["full_url"]

        log_embed = discord.Embed()
        log_embed.title = f"{ctx.channel.name} archived"
        log_embed.color = discord.Color.blurple()
        log_embed.add_field(name="Ticket Creator:", value=member.mention, inline=True)
        log_embed.add_field(name="Closed By:", value=ctx.user.mention, inline=True)
        log_embed.add_field(name="Ticket Subject:", value=ticket_subject, inline=False)
        log_embed.add_field(name="Ticket Message:", value=ticket_message, inline=False)
        log_embed.add_field(name="Participating Moderators:", value=value, inline=False)
        log_embed.add_field(name="Ticket Log:", value=url, inline=False)
        log_embed.set_thumbnail(url="https://i.imgur.com/A4c19BJ.png")

        ticket_log = discord.utils.get(ctx.guild.channels, id=config.channels.ticket_log)
        if ticket_log and isinstance(ticket_log, discord.TextChannel):
            await ticket_log.send(embed=log_embed)

        dm_embed = discord.Embed()
        dm_embed.title = "Ticket closed"
        dm_embed.description = (
            "Your ticket was closed. Please feel free to create a new ticket should you have any further inquiries."
        )
        dm_embed.color = discord.Color.blurple()
        dm_embed.add_field(name="Server:", value=f"[{ctx.guild.name}]({await ctx.guild.vanity_invite()})", inline=True)
        dm_embed.add_field(name="Ticket Log:", value=url, inline=False)
        dm_embed.set_image(url="https://i.imgur.com/bf3vqei.gif")

        try:
            await member.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            logger.info(f"Unable to send ticket log to {member} because their DM is closed")

        ticket.status = True
        ticket.log_url = url
        db.session.commit()

        await ctx.channel.delete()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketCog(bot))
