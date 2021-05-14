import logging
import re
from datetime import datetime, timedelta, timezone

import dataset
from discord.ext import commands
from discord.ext.commands import Bot, Cog, Context

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
    @commands.group(name="remind", aliases=["reminder", "remindme", "remind make", "remindmake"])
    async def remind_group(self, ctx: Context):
        """ Syntax: `!remindme <duration> <message>` """
        # regex derived from setsudo mute regex
        regex = r"(?:\s+(?:(\d+)\s*d(?:ays)?)?\s*(?:(\d+)\s*h(?:ours|rs|r)?)?\s*(?:(\d+)\s*m(?:inutes|in)?)?\s*(?:(\d+)\s*s(?:econds|ec)?)?)(?:\s+([\w\W]+))"

        try:
            match_list = re.findall(regex, ctx.message.content)[0]
        except:
            if ctx.invoked_subcommand is None:
                await ctx.send_help(ctx.command)
            return

        message = match_list[4]

        duration = dict(
            days = match_list[0],
            hours = match_list[1],
            minutes = match_list[2],
            seconds = match_list[3]
        )

        duration_string = ""

        time_duration = None
        
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
        end_time = datetime.now(tz=timezone.utc)+duration
        
        time_now = str(datetime.now(tz=timezone.utc))
        time_now = time_now[:time_now.index('.')]
        
        message = f"[This Message]({ctx.message.jump_url}) at {time_now} with the message:\n{message}"
        with dataset.connect(database.get_db()) as tx:
            tx["remind_me"].insert(dict(
                reminder_location=ctx.channel.id,
                author_id=ctx.author.id,
                date_to_remind=end_time.timestamp(),
                message=message,
                sent=False
            ))
        embed = embeds.make_embed(ctx=ctx, title="Reminder Set")
        embed.description = message+f"\nI'll remind you about this in {duration_string.strip()}."
        await ctx.reply(embed=embed)

    @remind_group.command(name='edit', enabled=False)
    async def edit(self, ctx: Context):
        """ Edit a reminder message. """
        # TODO

    @remind_group.command(name='list')
    async def _list(self, ctx: Context):
        """ List your reminders. """
        with dataset.connect(database.get_db()) as db:
            # Find all reminders from user and haven't been sent.
            remind_me = db['remind_me']
            result = remind_me.find(
                sent=False,
                author_id = ctx.author.id
            )
        
        reminders = []
        # Convert ResultSet to list.
        for reminder in result:
            alert_time = str(datetime.fromtimestamp(reminder['date_to_remind']))
            alert_time = alert_time[:alert_time.index('.')]
            reminders.append(f"**ID: {reminder['id']}** | Alert on {alert_time}\n{reminder['message']}")

        embed = embeds.make_embed(ctx=ctx, title="Reminders",
            image_url=config.remind_blurple, color="soft_blue")

        # Paginate results
        await LinePaginator.paginate(reminders, ctx=ctx, embed=embed, max_lines=5,
        max_size=2000, restrict_to_user=ctx.author)

    @remind_group.command(name='delete')
    async def delete(self, ctx: Context, reminder_id: int):
        """ Delete Reminders. User `reminder list` to find ID """
        with dataset.connect(database.get_db()) as db:
            # Find all reminders from user and haven't been sent.
            table = db['remind_me']
            result = table.find_one(id=reminder_id)
            if result is None:
                await embeds.error_message("Invalid ID", ctx)
                return
            if result['author_id'] != ctx.author.id:
                await embeds.error_message("This is not the reminder you are looking for", ctx)
                return
            if result['sent']:
                await embeds.error_message("This reminder has already been deleted", ctx)
                return
            
            # All the checks should be done.
            data = dict(id=reminder_id, sent=True)
            table.update(data, ['id'])
        embed = embeds.make_embed(ctx=ctx, title="Reminder deleted", 
            description=f"Reminder ID: {reminder_id} has been deleted.",
            image_url=config.remind_red, color="soft_red")
        await ctx.send(embed=embed)
    
    @remind_group.command(name='clear')
    async def clear_reminders(self, ctx):
        """ Clears all reminders. """
        with dataset.connect(database.get_db()) as db:
            remind_me = db['remind_me']
            result = remind_me.find(author_id = ctx.author.id, sent = False)
            for reminder in result:
                updated_data = dict(
                    id = reminder['id'],
                    sent = True
                )
                remind_me.update(updated_data, ['id'])
        
        await ctx.send("All your reminders have been cleared.")




def setup(bot: Bot) -> None:
    """ Load the Reminder cog. """
    bot.add_cog(Reminder(bot))
    log.info("Commands loaded: reminder")
