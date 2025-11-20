import arrow
import discord
from discord import app_commands
from discord.ext import commands, tasks
from loguru import logger
from sqlalchemy import select

from chiya import db
from chiya.config import config
from chiya.models import RemindMe
from chiya.utils import embeds
from chiya.utils.helpers import get_duration
from chiya.utils.pagination import MyMenuPages, MySource


class ReminderCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.check_for_reminder.start()

    async def cog_unload(self) -> None:
        self.check_for_reminder.cancel()

    @tasks.loop(seconds=3.0)
    async def check_for_reminder(self) -> None:
        """
        Checking for reminders to send
        """
        await self.bot.wait_until_ready()

        results = db.session.scalars(
            select(RemindMe).where(
                RemindMe.date_to_remind < arrow.utcnow().int_timestamp,
                RemindMe.sent.is_(False),
            )
        )

        if not results:
            return

        for reminder in results:
            try:
                user = await self.bot.fetch_user(reminder.author_id)
            except discord.errors.NotFound:
                reminder.sent = True
                db.session.commit()
                logger.warning(f"Reminder entry with ID {reminder.id} has an invalid user ID: {reminder.author_id}.")
                continue

            embed = discord.Embed()
            embed.title = "Here is your reminder"
            embed.description = reminder.message
            embed.color = discord.Color.blurple()

            try:
                channel = await user.create_dm()
                await channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Unable to post or DM {user}'s reminder {reminder.id=}.")

            reminder.sent = True
            db.session.commit()

    class Confirm(discord.ui.View):
        def __init__(self) -> None:
            super().__init__()
            self.value = None

        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            embed = discord.Embed()
            embed.description = f"{interaction.user.mention}, all your reminders have been cleared."
            embed.color = discord.Color.green()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            self.value = True
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            embed = discord.Embed()
            embed.description = f"{interaction.user.mention}, your request has been canceled."
            embed.color = discord.Color.blurple()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            self.value = False
            self.stop()

    group = app_commands.Group(name="reminder", description="Reminder management commands", guild_ids=[config.guild_id])

    @group.command(name="create", description="Set a reminder")
    @app_commands.describe(duration="Amount of time until the reminder is sent")
    @app_commands.describe(message="Reminder message")
    async def remindme(self, ctx: discord.Interaction, duration: str, message: str) -> None:
        """Creates a reminder message that will be sent at the specified time."""
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not ctx.channel:
            return

        duration_string, end_time = get_duration(duration=duration)
        if not duration_string:
            return await embeds.send_error(
                ctx=ctx,
                description=(
                    "Duration syntax: `y#mo#w#d#h#m#s` (year, month, week, day, hour, min, sec)\n"
                    "You can specify up to all seven but you only need one."
                ),
            )

        saved = RemindMe(
            reminder_location=ctx.channel.id,
            author_id=ctx.user.id,
            date_to_remind=end_time,
            message=message,
            sent=False,
        )
        db.session.add(saved)

        embed = discord.Embed()
        embed.title = "Reminder set"
        embed.description = f"I'll remind you about this <t:{end_time}:R>."
        embed.color = discord.Color.blurple()
        embed.add_field(name="ID:", value=saved.id, inline=False)
        embed.add_field(name="Message:", value=message, inline=False)
        embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)
        embed.set_footer(text="Make sure your DMs are open or you won't receive your reminder.")
        embed.set_thumbnail(url="https://i.imgur.com/VZV64W0.png")

        await ctx.followup.send(embed=embed)

    @group.command(name="edit", description="Edit an existing reminder")
    @app_commands.describe(reminder_id="The ID of the reminder to be updated")
    @app_commands.describe(new_message="The updated message for the reminder")
    async def edit(self, ctx: discord.Interaction, reminder_id: int, new_message: str) -> None:
        """
        Edit a reminder message.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        result = db.session.scalar(select(RemindMe).where(RemindMe.id == reminder_id))
        if not result:
            return await embeds.send_error(ctx, "That reminder ID doesn't exist.")

        if result.author_id != ctx.user.id:
            return await embeds.send_error(ctx, "That reminder is not yours.")

        if result.sent:
            return await embeds.send_error(ctx, "That reminder was already sent.")

        old_message = result.message
        result.message = new_message
        db.session.commit()

        embed = discord.Embed()
        embed.title = "Reminder set"
        embed.description = "Your reminder was updated"
        embed.color = discord.Color.green()
        embed.add_field(name="ID:", value=str(reminder_id), inline=False)
        embed.add_field(name="Old Message:", value=old_message, inline=False)
        embed.add_field(name="New Message:", value=new_message, inline=False)
        embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)
        embed.set_thumbnail(url="https://i.imgur.com/UUbR5J1.png")

        await ctx.followup.send(embed=embed)

    @group.command(name="list", description="List your existing reminders")
    async def list(self, ctx: discord.Interaction) -> None:
        """List your reminders."""
        await ctx.response.defer(ephemeral=True)

        results = db.session.scalars(
            select(RemindMe).where(
                RemindMe.author_id == ctx.user.id,
                RemindMe.sent.is_(False),
            )
        ).all()

        if not results:
            return await embeds.send_error(ctx=ctx, description="No reminders found!")

        embed = discord.Embed()
        embed.title = "Reminders"
        embed.color = discord.Color.blurple()
        embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)
        embed.set_thumbnail(url="https://i.imgur.com/VZV64W0.png")

        reminders = []
        for result in results:
            reminders.append(
                (f"**ID: {result.id}**\n**Alert on:** <t:{result.date_to_remind}:F>\n**Message: **{result.message}")
            )

        formatter = MySource(reminders, embed)
        menu = MyMenuPages(formatter)
        await menu.start(ctx)

    @group.command(name="delete", description="Delete an existing reminder")
    @app_commands.describe(reminder_id="The ID of the reminder to be deleted")
    async def delete(self, ctx: discord.Interaction, reminder_id: int) -> None:
        """
        Delete a reminder.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        result = db.session.scalar(select(RemindMe).where(RemindMe.id == reminder_id))
        if not result:
            return await embeds.send_error(ctx=ctx, description="Invalid ID.")

        if result.author_id != ctx.user.id:
            return await embeds.send_error(ctx=ctx, description="This reminder is not yours.")

        if result.sent:
            return await embeds.send_error(ctx=ctx, description="This reminder has already been deleted.")

        result.sent = True
        db.session.commit()

        embed = discord.Embed()
        embed.title = "Reminder deleted"
        embed.description = "Your reminder was deleted"
        embed.color = discord.Color.red()
        embed.add_field(name="ID:", value=str(reminder_id), inline=False)
        embed.add_field(name="Message:", value=result.message, inline=False)
        embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)
        embed.set_thumbnail(url="https://i.imgur.com/03bmvBX.png")

        await ctx.followup.send(embed=embed)

    @group.command(name="clear", description="Clears all of your existing reminders")
    async def clear(self, ctx: discord.Interaction) -> None:
        """
        Clears all reminders.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        embed = discord.Embed()
        embed.description = f"{ctx.user.mention}, clear all your reminders?"
        embed.color = discord.Color.blurple()

        view = self.Confirm()
        await ctx.followup.send(embed=embed, view=view)
        await view.wait()

        if not view.value:
            return

        results = db.session.scalars(
            select(RemindMe).where(
                RemindMe.author_id == ctx.user.id,
                RemindMe.sent.is_(False),
            )
        )

        for result in results:
            result.sent = True

        db.session.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderCog(bot))
