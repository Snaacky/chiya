import logging
from datetime import datetime, timezone

import discord
from discord.ext import tasks
from discord.ext.commands import Bot, Cog

from utils import database, embeds


log = logging.getLogger(__name__)


class ReminderTask(Cog):

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
        db = database.Database().get()

        # Find all reminders that are older than current time and have not been sent yet.
        remind_me = db["remind_me"]
        result = remind_me.find(sent=False, date_to_remind={"<": current_time})

        # If no results are found, simply terminate the db connection and return.
        if not result:
            return db.close()

        # Iterate over all the results found from the DB query if a result is found.
        for reminder in result:
            channel = self.bot.get_channel(reminder["reminder_location"])
            user = await self.bot.fetch_user(reminder["author_id"])
            embed = embeds.make_embed(
                title="Here is your reminder",
                description=reminder["message"],
                color="blurple"
            )

            # Attempt to send the reminder in the channel that it was created in. If fail, send it to their DM.
            if channel:
                try:
                    await channel.send(user.mention, embed=embed)
                except discord.HTTPException:
                    dm = await user.create_dm()
                    if not await dm.send(embed=embed):
                        log.warning(f"Unable to post or DM {user}'s reminder {reminder['id']=}.")

            # Mark the reminder as sent so it doesn't loop again.
            remind_me.update(dict(id=reminder["id"], sent=True), ["id"])

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    bot.add_cog(ReminderTask(bot))
    log.info("Task loaded: reminder")
