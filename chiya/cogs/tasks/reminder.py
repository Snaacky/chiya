from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks
from loguru import logger as log

from chiya import database
from chiya.utils import embeds


class ReminderTasks(commands.Cog):
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
            try:
                user = await self.bot.fetch_user(reminder["author_id"])
            except Exception:  # TODO: Add a proper Exception here
                db["remind_me"].update(dict(id=reminder["id"], sent=True), ["id"])
                log.warning(f"Reminder entry with ID {reminder['id']} has an invalid user ID: {reminder['author_id']}.")
                continue

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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderTasks(bot))
    log.info("Tasks loaded: reminder")
