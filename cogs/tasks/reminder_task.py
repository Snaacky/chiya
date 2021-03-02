import asyncio
import logging
import traceback
from datetime import datetime

import dataset
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Cog

from utils import database, embeds

log = logging.getLogger(__name__)


class ReminderTask(Cog):
    """ Reminder Background Task """
    def __init__(self, bot: Bot):
        self.bot = bot
        self.check_for_reminder.start()

    def cog_unload(self):
        self.check_for_reminder.cancel()

    # Loop 3 seconds to avoid ravaging the CPU and Reddit's API.
    @tasks.loop(seconds=3.0)
    async def check_for_reminder(self) -> None:
        """ Checking for reminders to send """
        # Wait for bot to start.
        await self.bot.wait_until_ready()

        try:
            # Get current time to compare.
            current_time = datetime.utcnow()
            current_time = format(current_time, '%Y-%m-%d %H:%M:%S')
            with dataset.connect(database.get_db()) as db:
                # Find all reminders that are older than current time and have not been sent.
                statement = f"SELECT id, reminder_location, author_id, message FROM remind_me WHERE date_to_remind < '{current_time}' AND sent = FALSE"
                result = db.query(statement)
            for reminder in result:
                # Find the channel.
                channel = self.bot.get_channel(reminder['reminder_location'])
                # Find the User.
                user = self.bot.get_user(reminder['author_id'])

                embed = embeds.make_embed(title=f"Here is your reminder",
                    description= reminder['message'])
                try:
                    await channel.send(user.mention, embed=embed)
                    # Update database to flag that message was sent.
                    table = db["remind_me"]
                    data = dict(id=reminder['id'], sent=True)
                    table.update(data, ['id'])
                except:
                    log.warn(f"Unable to post reminder for {reminder['id']=}")
        
        # Catch all exceptions to avoid crashing and log the traceback for future debugging.
        except Exception as e:
            log.error("remind me task broke", exc_info=e)
            traceback.print_exc()


def setup(bot: Bot) -> None:
    """ Load the ReminderTask cog. """
    bot.add_cog(ReminderTask(bot))
    log.info("Cog loaded: reminder_task")
