import asyncio

import discord
from discord.ext import commands
from discord import app_commands
from loguru import logger as log

from chiya import database
from chiya.config import config
from chiya.utils import embeds
from chiya.utils.helpers import get_duration
from chiya.utils.pagination import MyMenuPages, MySource


class ReminderCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    class Confirm(discord.ui.View):
        def __init__(self):
            super().__init__()
            self.value = None

        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = embeds.make_embed(
                description=f"{interaction.user.mention}, all your reminders have been cleared.",
                color=discord.Color.green(),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            self.value = True
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = embeds.make_embed(
                description=f"{interaction.user.mention}, your request has been canceled.",
                color=discord.Color.blurple(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            self.value = False
            self.stop()

    @app_commands.guilds(config.guild_id)
    @app_commands.guild_only()
    class ReminderGroup(app_commands.Group):
        pass

    reminder = ReminderGroup(name="reminder", guild_ids=[config.guild_id])

    @reminder.command(name="create", description="Set a reminder")
    @app_commands.describe(duration="Amount of time until the reminder is sent")
    @app_commands.describe(message="Reminder message")
    async def remindme(
        self,
        ctx: discord.Interaction,
        duration: str,
        message: str,
    ) -> None:
        """Creates a reminder message that will be sent at the specified time."""
        await ctx.response.defer(thinking=True, ephemeral=True)

        duration_string, end_time = get_duration(duration=duration)
        if not duration_string:
            return await embeds.error_message(
                ctx=ctx,
                description=(
                    "Duration syntax: `y#mo#w#d#h#m#s` (year, month, week, day, hour, min, sec)\n"
                    "You can specify up to all seven but you only need one."
                ),
            )

        db = database.Database().get()
        remind_id = db["remind_me"].insert(
            dict(
                reminder_location=ctx.channel.id,
                author_id=ctx.user.id,
                date_to_remind=end_time,
                message=message,
                sent=False,
            )
        )

        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title="Reminder set",
            description=f"I'll remind you about this <t:{end_time}:R>.",
            thumbnail_url="https://i.imgur.com/VZV64W0.png",
            color=discord.Color.blurple(),
            fields=[
                {"name": "ID:", "value": remind_id, "inline": False},
                {"name": "Message:", "value": message, "inline": False},
            ],
            footer="Make sure your DMs are open or you won't receive your reminder.",
        )

        await ctx.followup.send(embed=embed)

    @reminder.command(name="edit", description="Edit an existing reminder")
    @app_commands.describe(reminder_id="The ID of the reminder to be updated")
    @app_commands.describe(new_message="The updated message for the reminder")
    async def edit(
        self,
        ctx: discord.Interaction,
        reminder_id: int,
        new_message: str,
    ) -> None:
        """
        Edit a reminder message.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        db = database.Database().get()

        remind_me = db["remind_me"]
        result = remind_me.find_one(id=reminder_id)
        old_message = result["message"]

        if result["author_id"] != ctx.user.id:
            return await embeds.error_message(ctx, "That reminder is not yours.")

        if result["sent"]:
            return await embeds.error_message(ctx, "That reminder doesn't exist.")

        data = dict(id=result["id"], message=new_message)
        remind_me.update(data, ["id"])

        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title="Reminder set",
            description="Your reminder was updated",
            thumbnail_url="https://i.imgur.com/UUbR5J1.png",
            color=discord.Color.green(),
            fields=[
                {"name": "ID:", "value": str(reminder_id), "inline": False},
                {"name": "Old Message:", "value": old_message, "inline": False},
                {"name": "New Message:", "value": new_message, "inline": False},
            ],
        )

        await ctx.followup.send(embed=embed)

    @reminder.command(name="list", description="List your existing reminders")
    async def list(self, ctx: discord.Interaction) -> None:
        """List your reminders."""
        await ctx.response.defer(ephemeral=True)

        db = database.Database().get()
        results = db["remind_me"].find(sent=False, author_id=ctx.user.id)
        reminders = []
        for result in results:
            reminders.append(
                (
                    f"**ID: {result['id']}**\n"
                    f"**Alert on:** <t:{result['date_to_remind']}:F>\n"
                    f"**Message: **{result['message']}"
                )
            )

        if not reminders:
            return await embeds.error_message(ctx=ctx, description="No reminders found!")

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title="Reminders",
            thumbnail_url="https://i.imgur.com/VZV64W0.png",
            color=discord.Color.blurple(),
        )

        formatter = MySource(reminders, embed)
        menu = MyMenuPages(formatter)
        await menu.start(ctx)

        db.close()

    @reminder.command(name="delete", description="Delete an existing reminder")
    @app_commands.describe(reminder_id="The ID of the reminder to be deleted")
    async def delete(
        self,
        ctx: discord.Interaction,
        reminder_id: int,
    ) -> None:
        """
        Delete a reminder.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        db = database.Database().get()

        table = db["remind_me"]
        result = table.find_one(id=reminder_id)

        if not result:
            return await embeds.error_message(ctx=ctx, description="Invalid ID.")

        if result["author_id"] != ctx.user.id:
            return await embeds.error_message(ctx=ctx, description="This reminder is not yours.")

        if result["sent"]:
            return await embeds.error_message(ctx=ctx, description="This reminder has already been deleted.")

        data = dict(id=reminder_id, sent=True)
        table.update(data, ["id"])

        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title="Reminder deleted",
            description="Your reminder was deleted",
            thumbnail_url="https://i.imgur.com/03bmvBX.png",
            color=discord.Color.red(),
            fields=[
                {"name": "ID:", "value": str(reminder_id), "inline": False},
                {"name": "Message: ", "value": result["message"], "inline": False},
            ],
        )
        await ctx.followup.send(embed=embed)

    @reminder.command(name="clear", description="Clears all of your existing reminders")
    async def clear(self, ctx: discord.Interaction) -> None:
        """
        Clears all reminders.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        db = database.Database().get()

        confirm_embed = embeds.make_embed(
            description=f"{ctx.user.mention}, clear all your reminders?",
            color=discord.Color.blurple(),
        )

        view = self.Confirm()
        await ctx.followup.send(embed=confirm_embed, view=view)
        await view.wait()

        if not view.value or view.value is None:
            db.close()
            return

        remind_me = db["remind_me"]
        results = remind_me.find(author_id=ctx.user.id, sent=False)
        for result in results:
            updated_data = dict(id=result["id"], sent=True)
            remind_me.update(updated_data, ["id"])

        db.commit()
        db.close()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderCommands(bot))
    log.info("Commands loaded: reminder")
