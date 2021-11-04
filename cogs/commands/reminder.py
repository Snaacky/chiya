import logging
from datetime import datetime

from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

import utils.duration
from utils import database, embeds
from utils.config import config
from utils.pagination import LinePaginator


log = logging.getLogger(__name__)


class Reminder(Cog):

    def __init__(self, bot: Bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="remindme",
        description="Sets a reminder note to be sent at a future date",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="duration",
                description="How long until you want the reminder to be sent",
                option_type=3,
                required=True
            ),
            create_option(
                name="message",
                description="The message that you want to be reminded of",
                option_type=3,
                required=True
            ),
        ]
    )
    async def remind(self, ctx: SlashContext, duration: str, message: str):
        """ Sets a reminder message. """
        await ctx.defer()

        # Get the duration string for embed and ban end time for the specified duration.
        duration_string, end_time = utils.duration.get_duration(duration=duration)
        # If the duration string is empty due to Regex not matching anything, send and error embed and return.
        if not duration_string:
            return await embeds.error_message(
                ctx=ctx,
                description=(
                    "Duration syntax: `#d#h#m#s` (day, hour, min, sec)\n"
                    "You can specify up to all four but you only need one."
                )
            )

        # Open a connection to the database.
        db = database.Database().get()

        remind_id = db["remind_me"].insert(dict(
            reminder_location=ctx.channel.id,
            author_id=ctx.author.id,
            date_to_remind=end_time,
            message=message,
            sent=False
        ))

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Reminder set",
            description=f"\nI'll remind you about this in {duration_string[:-1]}.",  # Remove the trailing white space.
            thumbnail_url="https://i.imgur.com/VZV64W0.png",
            color="blurple"
        )
        embed.add_field(name="ID: ", value=remind_id, inline=False)
        embed.add_field(name="Message:", value=message, inline=False)
        await ctx.send(embed=embed)

    @cog_ext.cog_subcommand(
        base="reminder",
        name="edit",
        description="Edit an existing reminder",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="reminder_id",
                description="The ID of the reminder to be updated",
                option_type=3,
                required=True
            ),
            create_option(
                name="new_message",
                description="The updated message for the reminder",
                option_type=3,
                required=True
            ),
        ]
    )
    async def edit_reminder(self, ctx: SlashContext, reminder_id: int, new_message: str):
        """ Edit a reminder message. """
        await ctx.defer()

        # Open a connection to the database.
        db = database.Database().get()

        remind_me = db["remind_me"]
        reminder = remind_me.find_one(id=reminder_id)
        old_message = reminder["message"]

        if reminder["author_id"] != ctx.author.id:
            return await embeds.error_message(ctx, "That reminder isn't yours, so you can't edit it.")

        if reminder["sent"]:
            return await embeds.error_message(ctx, "That reminder doesn't exist.")

        data = dict(id=reminder["id"], message=new_message)
        remind_me.update(data, ["id"])

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Reminder set",
            description="Your reminder was updated",
            thumbnail_url="https://i.imgur.com/UUbR5J1.png",
            color="soft_green"
        )
        embed.add_field(name="ID: ", value=str(reminder_id), inline=False)
        embed.add_field(name="Old Message: ", value=old_message, inline=False)
        embed.add_field(name="New Message: ", value=new_message, inline=False)
        await ctx.send(embed=embed)

    @cog_ext.cog_subcommand(
        base="reminder",
        name="list",
        description="List your existing reminders",
        guild_ids=[config["guild_id"]],
    )
    async def list_reminders(self, ctx: SlashContext):
        """ List your reminders. """
        await ctx.defer()

        # Open a connection to the database.
        db = database.Database().get()

        # Find all reminders from user and haven't been sent.
        remind_me = db["remind_me"]
        result = remind_me.find(sent=False, author_id=ctx.author.id)

        reminders = []

        # Convert ResultSet to list.
        for reminder in result:
            alert_time = datetime.fromtimestamp(reminder["date_to_remind"])
            # https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
            alert_time = alert_time.strftime("%A, %b %d, %Y at %X")
            reminders.append(f"**ID: {reminder['id']}** \n"
                             f"**Alert on:** {alert_time} UTC\n"
                             f"**Message: **{reminder['message']}")

        embed = embeds.make_embed(
            ctx=ctx,
            title="Reminders",
            thumbnail_url="https://i.imgur.com/VZV64W0.png",
            color="blurple"
        )

        # Close the connection to the database.
        db.close()

        # Paginate results.
        await LinePaginator.paginate(reminders, ctx=ctx, embed=embed, max_lines=5,
                                     max_size=2000, restrict_to_user=ctx.author)

    @cog_ext.cog_subcommand(
        base="reminder",
        name="delete",
        description="Delete an existing reminder",
        guild_ids=[config["guild_id"]],
        options=[
            create_option(
                name="reminder_id",
                description="The ID of the reminder deleted",
                option_type=4,
                required=True
            ),
        ]
    )
    async def delete_reminder(self, ctx: SlashContext, reminder_id: int):
        """ Delete Reminders. User `reminder list` to find ID """
        await ctx.defer()

        # Open a connection to the database.
        db = database.Database().get()

        # Find all reminders from user and haven't been sent.
        table = db["remind_me"]
        reminder = table.find_one(id=reminder_id)

        if not reminder:
            return await embeds.error_message(ctx=ctx, description="Invalid ID.")

        if reminder["author_id"] != ctx.author.id:
            return await embeds.error_message(ctx=ctx, description="This reminder is not yours.")

        if reminder["sent"]:
            return await embeds.error_message(ctx=ctx, description="This reminder has already been deleted.")

        # All the checks should be done.
        data = dict(id=reminder_id, sent=True)
        table.update(data, ["id"])

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Reminder deleted",
            description="Your reminder was deleted",
            thumbnail_url="https://i.imgur.com/03bmvBX.png",
            color="soft_red"
        )
        embed.add_field(name="ID: ", value=str(reminder_id), inline=False)
        embed.add_field(name="Message: ", value=reminder["message"], inline=False)
        await ctx.send(embed=embed)

    @cog_ext.cog_subcommand(
        base="reminder",
        name="clear",
        description="Clears all of your existing reminders",
        guild_ids=[config["guild_id"]]
    )
    async def clear_reminders(self, ctx: SlashContext):
        """ Clears all reminders. """
        await ctx.defer()

        # Open a connection to the database.
        db = database.Database().get()

        remind_me = db["remind_me"]
        result = remind_me.find(author_id=ctx.author.id, sent=False)
        for reminder in result:
            updated_data = dict(id=reminder["id"], sent=True)
            remind_me.update(updated_data, ["id"])

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

        await ctx.send("All your reminders have been cleared.")


def setup(bot: Bot) -> None:
    bot.add_cog(Reminder(bot))
    log.info("Commands loaded: reminder")
