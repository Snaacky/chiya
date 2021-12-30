import asyncio
import logging
from datetime import datetime
from typing import Optional

import discord
from discord.commands import Option, SlashCommandGroup, context, slash_command
from discord.ext import commands

import utils.duration
from utils import database, embeds
from utils.config import config
from utils.pagination import LinePaginator

log = logging.getLogger(__name__)


class ReminderCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    reminder = SlashCommandGroup(
        "reminder",
        "Sets a reminder note to be sent at a future date",
        guild_ids=config["guild_ids"],
    )

    @slash_command(guild_ids=config["guild_ids"], description="Set a reminder")
    async def remindme(
        self,
        ctx: context.ApplicationContext,
        duration: Option(str, description="Amount of time until the reminder is sent", required=True),
        message: Option(str, description="Reminder message", required=True),
    ) -> Optional[discord.Embed]:
        """ Set a reminder message. """
        await ctx.defer()

        duration_string, end_time = utils.duration.get_duration(duration=duration)
        if not duration_string:
            return await embeds.error_message(
                ctx=ctx,
                description=(
                    "Duration syntax: `#d#h#m#s` (day, hour, min, sec)\n"
                    "You can specify up to all four but you only need one."
                ))

        db = database.Database().get()
        remind_id = db["remind_me"].insert(
            dict(
                reminder_location=ctx.channel.id,
                author_id=ctx.author.id,
                date_to_remind=end_time,
                message=message,
                sent=False,
            ))

        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title="Reminder set",
            description=f"\nI'll remind you about this in {duration_string[:-1]}.",  # Remove the trailing white space.
            thumbnail_url="https://i.imgur.com/VZV64W0.png",
            color=discord.Color.blurple(),
            fields=[
                {"name": "ID:", "value": remind_id, "inline": False},
                {"name": "Message:", "value": message, "inline": False},
            ])

        await ctx.send_followup(embed=embed)

    @reminder.command(name="edit", descrption="Edit an existing reminder")
    async def edit(
        self,
        ctx: context.ApplicationContext,
        reminder_id: Option(int, description="The ID of the reminder to be updated", required=True),
        new_message: Option(str, description="The updated message for the reminder", required=True),
    ) -> Optional[discord.Embed]:
        """ Edit a reminder message. """
        await ctx.defer()

        db = database.Database().get()

        remind_me = db["remind_me"]
        result = remind_me.find_one(id=reminder_id)
        old_message = result["message"]

        if result["author_id"] != ctx.author.id:
            return await embeds.error_message(ctx, "That reminder isn't yours, so you can't edit it.")

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
            ])

        await ctx.send_followup(embed=embed)

    @reminder.command(name="list", description="List your existing reminders")
    async def list(self, ctx: context.ApplicationContext) -> None:
        """ List your reminders. """
        await ctx.defer()

        db = database.Database().get()

        results = db["remind_me"].find(sent=False, author_id=ctx.author.id)

        reminders = []
        for result in results:
            alert_time = datetime.fromtimestamp(result["date_to_remind"])
            alert_time = alert_time.strftime("%A, %b %d, %Y at %X")
            reminders.append(
                f"**ID: {result['id']}** \n"
                f"**Alert on:** {alert_time} UTC\n"
                f"**Message: **{result['message']}"
            )

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title="Reminders",
            thumbnail_url="https://i.imgur.com/VZV64W0.png",
            color=discord.Color.blurple(),
        )

        await LinePaginator.paginate(
            reminders,
            ctx=ctx,
            embed=embed,
            max_lines=5,
            max_size=2000,
            restrict_to_user=ctx.author,
        )

        db.close()

    @reminder.command(name="delete", description="Delete an existing reminder")
    async def delete(
        self,
        ctx: context.ApplicationContext,
        reminder_id: Option(int, description="The ID of the reminder to be deleted", required=True),
    ):
        """ Delete a reminder. """
        await ctx.defer()

        db = database.Database().get()

        table = db["remind_me"]
        result = table.find_one(id=reminder_id)

        if not result:
            return await embeds.error_message(ctx=ctx, description="Invalid ID.")

        if result["author_id"] != ctx.author.id:
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
            ])
        await ctx.send_followup(embed=embed)

    @reminder.command(name="clear", description="Clears all of your existing reminders")
    async def clear(self, ctx: context.ApplicationContext) -> Optional[discord.Embed]:
        """Clears all reminders."""
        await ctx.defer()

        db = database.Database().get()

        confirm_embed = embeds.make_embed(
            description=f"{ctx.author.mention}, clear all your reminders? (yes/no/y/n)",
            color=discord.Color.blurple(),
        )

        await ctx.send_followup(embed=confirm_embed)

        def check(message):
            return (
                    message.author == ctx.author
                    and message.channel == ctx.channel
                    and message.content.lower() in ("yes", "no", "y", "n")
            )

        try:
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            if msg.content.lower() in ("no", "n"):
                db.close()
                embed = embeds.error_message(ctx, description=f"{ctx.author.mention}, your request has been canceled.")
                return await ctx.send_followup(embed=embed)
        except asyncio.TimeoutError:
            db.close()
            embed = embeds.error_message(ctx, description=f"{ctx.author.mention}, your request has timed out.")
            return await ctx.send_followup(embed=embed)

        remind_me = db["remind_me"]
        results = remind_me.find(author_id=ctx.author.id, sent=False)
        for result in results:
            updated_data = dict(id=result["id"], sent=True)
            remind_me.update(updated_data, ["id"])

        embed = embeds.make_embed(
            description=f"{ctx.author.mention}, all your reminders have been cleared.",
            color=discord.Color.green(),
        )

        await ctx.send_followup(embed=embed)

        db.commit()
        db.close()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ReminderCommands(bot))
    log.info("Commands loaded: reminder")
