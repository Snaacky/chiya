import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from utils import database, embeds


log = logging.getLogger(__name__)


class ReminderTask(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.check_for_reminder.start()

    def cog_unload(self) -> None:
        self.check_for_reminder.cancel()

    @tasks.loop(seconds=3.0)
    async def check_for_reminder(self) -> None:
        """
        Checking for reminders to send
        """
        await self.bot.wait_until_ready()

        db = database.Database().get()
        result = db["remind_me"].find(sent=False, date_to_remind={"<": datetime.now(tz=timezone.utc).timestamp()})

        if not result:
            return db.close()

        for reminder in result:
            channel = self.bot.get_channel(reminder["reminder_location"])
            user = await self.bot.fetch_user(reminder["author_id"])
            embed = embeds.make_embed(title="Here is your reminder", description=reminder["message"], color="blurple")

            if channel:
                try:
                    await channel.send(user.mention, embed=embed)
                except discord.HTTPException:
                    dm = await user.create_dm()
                    if not await dm.send(embed=embed):
                        log.warning(f"Unable to post or DM {user}'s reminder {reminder['id']=}.")

            db["remind_me"].update(dict(id=reminder["id"], sent=True), ["id"])

        db.commit()
        db.close()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ReminderTask(bot))
    log.info("Task loaded: reminder")
