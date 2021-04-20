import asyncio
import logging
import time
import traceback
from datetime import datetime

import dataset
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Cog

from utils import database, embeds
import config

log = logging.getLogger(__name__)


class TimedModActionsTask(Cog):
    """ Timed Mod Actions Background  """
    def __init__(self, bot: Bot):
        self.bot = bot
        self.check_mod_actions.start()

    def cog_unload(self):
        self.check_mod_actions.cancel()

    
    @tasks.loop(seconds=3.0)
    async def check_mod_actions(self) -> None:
        """ Checks for mod actions periodically, and reverses them accordingly if the time lapsed. """
        db = dataset.connect(database.get_db())
        timed_actions = db["timed_mod_actions"]


    async def _unmute(member: discord.Member):
        """ Unmutes member and logs the action. """

    async def _unban(user: discord.User):
        """ Unbans member and logs the action. """





def setup(bot: Bot) -> None:
    """ Load the ReminderTask cog. """
    bot.add_cog(ReminderTask(bot))
    log.info("Cog loaded: reminder_task")