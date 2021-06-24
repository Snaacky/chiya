import logging
import re
from datetime import datetime, timedelta, timezone

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

import config
from utils import database, embeds
from utils.pagination import LinePaginator
from utils.record import record_usage

log = logging.getLogger(__name__)


class Reminder(Cog):
    """ Handles reminder commands """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.bot_has_permissions(ban_members=True, send_messages=True)
    @cog_ext.cog_slash(
        name="remindme",
        description="Sets a reminder note to be sent at a future date",
        guild_ids=[config.guild_id],
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

        # RegEx stolen from Setsudo and modified
        regex = r"(?<=^)(?:(?:(\d+)\s*d(?:ays)?)?\s*(?:(\d+)\s*h(?:ours|rs|r)?)?\s*(?:(\d+)\s*m(?:inutes|in)?)?\s*(?:(\d+)\s*s(?:econds|ec)?)?)"

        # Get all of the matches from the RegEx.
        try:
            match_list = re.findall(regex, duration)[0]
        except discord.HTTPException:
            await embeds.error_message(ctx=ctx, description="Duration syntax: `#d#h#m#s` (day, hour, min, sec)\nYou can specify up to all four but you only need one.")
            return

        # Check if all the matches are blank and return preemptively if so.
        if not any(x.isalnum() for x in match_list):
            await embeds.error_message(ctx=ctx, description="Duration syntax: `#d#h#m#s` (day, hour, min, sec)\nYou can specify up to all four but you only need one.")
            return

        duration = dict(
            days=match_list[0],
            hours=match_list[1],
            minutes=match_list[2],
            seconds=match_list[3]
        )

        duration_string = ""

        for key in duration:
            if len(duration[key]) > 0:
                duration_string += f"{duration[key]} {key} "
                duration[key] = float(duration[key])
            else:
                duration[key] = 0

        duration = timedelta(
            days=duration['days'],
            hours=duration['hours'],
            minutes=duration['minutes'],
            seconds=duration['seconds']
        )

        end_time = datetime.now(tz=timezone.utc) + duration
        time_now = str(datetime.now(tz=timezone.utc))
        time_now = time_now[:time_now.index('.')]

        with dataset.connect(database.get_db()) as tx:
            tx["remind_me"].insert(dict(
                reminder_location=ctx.channel.id,
                author_id=ctx.author.id,
                date_to_remind=end_time.timestamp(),
                message=message,
                sent=False
            ))
        embed = embeds.make_embed(ctx=ctx, title="Reminder Set")
        embed.description = f"\nI'll remind you about this in {duration_string.strip()}."
        embed.add_field(name="Message:", value=message)
        await ctx.send(embed=embed)

    @cog_ext.cog_subcommand(
        base="reminder",
        name="edit",
        description="Edit an existing reminder",
        guild_ids=[config.guild_id],
        options=[
            create_option(
                name="id",
                description="The ID of the reminder to be updated",
                option_type=3,
                required=True
            ),
            create_option(
                name="message",
                description="The updated message for the reminder",
                option_type=3,
                required=True
            ),
        ]
    )
    async def edit_reminder(self, ctx: SlashContext, id: int, new_message: str):
        """ Edit a reminder message. """
        await ctx.defer()

        with dataset.connect(database.get_db()) as db:
            remind_me = db['remind_me']
            reminder = remind_me.find_one(id=id)

            if reminder['author_id'] != ctx.author.id:
                await embeds.error_message(ctx, "That reminder isn't yours, so you can't edit it.")
                return

            if reminder['sent']:
                await embeds.error_message(ctx, "That reminder doesn't exist.")
                return

            data = dict(id=reminder['id'], message=new_message)
            remind_me.update(data, ['id'])

        await ctx.send("Reminder was updated.")

    @cog_ext.cog_subcommand(
        base="reminder",
        name="list",
        description="List your existing reminders",
        guild_ids=[config.guild_id],
    )
    async def list_reminders(self, ctx: SlashContext):
        """ List your reminders. """
        await ctx.defer()

        with dataset.connect(database.get_db()) as db:
            # Find all reminders from user and haven't been sent.
            remind_me = db['remind_me']
            result = remind_me.find(sent=False, author_id=ctx.author.id)

        reminders = []

        # Convert ResultSet to list.
        for reminder in result:
            alert_time = str(datetime.fromtimestamp(reminder['date_to_remind']))
            alert_time = alert_time[:alert_time.index('.')]
            reminders.append(f"**ID: {reminder['id']}** | Alert on {alert_time}\n{reminder['message']}")

        embed = embeds.make_embed(
            ctx=ctx,
            title="Reminders",
            thumbnail_url=config.remind_blurple,
            color="blurple"
        )

        # Paginate results
        await LinePaginator.paginate(reminders, ctx=ctx, embed=embed, max_lines=5,
                                     max_size=2000, restrict_to_user=ctx.author)

    @cog_ext.cog_subcommand(
        base="reminder",
        name="delete",
        description="Delete an existing reminder",
        guild_ids=[config.guild_id],
        options=[
            create_option(
                name="id",
                description="The ID of the reminder deleted",
                option_type=3,
                required=True
            ),
        ]
    )
    async def delete_reminder(self, ctx: SlashContext, reminder_id: int):
        """ Delete Reminders. User `reminder list` to find ID """
        await ctx.defer()

        with dataset.connect(database.get_db()) as db:
            # Find all reminders from user and haven't been sent.
            table = db['remind_me']
            result = table.find_one(id=reminder_id)

            if not result:
                await embeds.error_message(ctx=ctx, description="Invalid ID")
                return

            if result['author_id'] != ctx.author.id:
                await embeds.error_message(ctx=ctx, description="This is not the reminder you are looking for")
                return

            if result['sent']:
                await embeds.error_message(ctx=ctx, description="This reminder has already been deleted")
                return

            # All the checks should be done.
            data = dict(id=reminder_id, sent=True)
            table.update(data, ['id'])

        embed = embeds.make_embed(
            ctx=ctx,
            title="Reminder deleted",
            description=f"Reminder ID: {reminder_id} has been deleted.",
            thumbnail_url=config.remind_red,
            color="soft_red"
        )
        await ctx.send(embed=embed)

    @cog_ext.cog_subcommand(
        base="reminder",
        name="clear",
        description="Clears all of your existing reminders",
        guild_ids=[config.guild_id]
    )
    async def clear_reminders(self, ctx: SlashContext):
        """ Clears all reminders. """
        await ctx.defer()

        with dataset.connect(database.get_db()) as db:
            remind_me = db['remind_me']
            result = remind_me.find(author_id=ctx.author.id, sent=False)
            for reminder in result:
                updated_data = dict(id=reminder['id'], sent=True)
                remind_me.update(updated_data, ['id'])

        await ctx.send("All your reminders have been cleared.")


def setup(bot: Bot) -> None:
    """ Load the Reminder cog. """
    bot.add_cog(Reminder(bot))
    log.info("Commands loaded: reminder")
