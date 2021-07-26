import logging
from datetime import datetime, timezone

import dataset
import discord
from discord.ext import tasks
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

    @tasks.loop(seconds=3.0)
    async def check_for_reminder(self) -> None:
        """ Checking for reminders to send """
        await self.bot.wait_until_ready()

        # Get current time to compare.
        current_time = datetime.now(tz=timezone.utc).timestamp()

        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        # Find all reminders that are older than current time and have not been sent yet.
        remind_me = db["remind_me"]
        result = remind_me.find(sent=False, date_to_remind={"<": current_time})

        # Iterate over all the results found from the DB query above.
        for reminder in result:
            channel = self.bot.get_channel(reminder["reminder_location"])
            user = self.bot.get_user(reminder["author_id"])
            embed = embeds.make_embed(title=f"Here is your reminder", description=reminder["message"])
            table = db["remind_me"]

            # Mark the reminder as sent so it doesn't loop again.
            table.update(dict(id=reminder["id"], sent=True), ["id"])

            # Attempt to send the reminder in the channel that it was created in.
            try:
                await channel.send(user.mention, embed=embed)
                log.info(f"Sent {user}'s {reminder['id']=} in {channel}")
                return
            except discord.HTTPException:
                log.warning(f"Tried to post reminder for {user}'s {reminder['id']=} but don't have access to the channel")

                # If unable to send the reminder in the channel it was created in, attempt to DM it to the user.
                try:
                    dm = await user.create_dm()
                    await dm.send(embed=embed)
                    table.update(dict(id=reminder['id'], sent=True), ['id'])
                    log.info(f"Sent {user}'s {reminder['id']=} via DMs because I couldn't access channel {channel} ({reminder['reminder_location']})")
                except discord.HTTPException:
                    log.warning(f"Unable to post {user}'s reminder {reminder['id']=} and the user has DMs blocked")
        
        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """ Load the ReminderTask cog. """
    bot.add_cog(ReminderTask(bot))
    log.info("Task loaded: reminder")
