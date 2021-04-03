import logging
import re
import time
from datetime import datetime

import dataset
import parsedatetime.parsedatetime as pdt
from discord.ext import commands
from discord.ext.commands import Bot, Cog, Context

import config
from utils import database, embeds
from utils.pagination import LinePaginator
from utils.record import record_usage

log = logging.getLogger(__name__)


class Reminder(Cog):
    """ Handels reminder commands """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.group(name="remind", aliases=["reminder", "remindme"])
    async def remind_group(self, ctx: Context):
        """ Make a message to remind you in the future. """
        if ctx.invoked_subcommand is None:
            # Send the help command for this group
            await ctx.send_help(ctx.command)

    @remind_group.command(name='make', aliases=["me"])
    async def make(self, ctx: Context, *, time_with_message_in_quotes: str):
        """ !Remind Me TIME_HERE "MESSAGE" (with quotes) """

        # Spliting date and message
        message_split = time_with_message_in_quotes.split('"', 1)
        if len(message_split) == 2 and message_split[1].endswith('"'):
            message_split[1] = message_split[1][:-1]

        cal = pdt.Calendar()
        # Convert text to a date somehow.
        replyDate = cal.parse(message_split[0], ctx.message.created_at)

        # date too long or unknown input.
        if replyDate[1] == 0:
            # default time: 1 day.
            replyDate = cal.parse("1 day", ctx.message.created_at)
            replyMessage = "**Defaulted to one day.**\n\n"
        # Converting time.
        # 9999/12/31 HH/MM/SS.
        date_to_remind = time.strftime('%Y-%m-%d %H:%M:%S', replyDate[0])

        # Making message to store.
        current_time = ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        message = (f"[**This message**]({ctx.message.jump_url}) from " +
            f"[**{current_time} UTC**](http://www.wolframalpha.com/input/?i="
            f"{current_time.replace(' ', '+')}+UTC+To+Local+Time):\n"
            f"{message_split[1]}")

        with dataset.connect(database.get_db()) as tx:
            tx["remind_me"].insert(dict(
                reminder_location=ctx.channel.id,
                author_id=ctx.author.id,
                date_to_remind=date_to_remind,
                message=message,
                sent=False
            ))
        embed = embeds.make_embed(context=ctx, title="Reminder Set",
            description="I will be messaging you here on "
        f"[**{date_to_remind} UTC**](http://www.wolframalpha.com/input/?i="
        f"{date_to_remind.replace(' ', '+')}+UTC+To+Local+Time)\n\n"
        f"{message}",
        image_url=config.remind_green, color=config.soft_green)
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
            statement = f"SELECT id, date_to_remind, message FROM remind_me WHERE author_id = {ctx.author.id} AND sent = FALSE"
            result = db.query(statement)
        
        messages = []
        # Convert dict to list.
        for message in result:
            alert_time = (f"[**{message['date_to_remind']} UTC**](http://www.wolframalpha.com/input/?i="
                f"{message['date_to_remind'].replace(' ', '+')}+UTC+To+Local+Time):")
            messages.append(f"**ID: {message['id']}** | Alert on {alert_time}\n{message['message']}")

        embed = embeds.make_embed(context=ctx, title="Reminders",
            image_url=config.remind_blurple, color=config.soft_blue)

        # Paginate results
        await LinePaginator.paginate(messages, ctx=ctx, embed=embed, max_lines=5,
        max_size=2000, restrict_to_user=ctx.author)

    @remind_group.command(name='delete')
    async def delete(self, ctx: Context, reminder_id: int):
        """ Delete Reminders. User `reminder list` to find ID """
        with dataset.connect(database.get_db()) as db:
            # Find all reminders from user and haven't been sent.
            table = db.load_table('remind_me')
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
        embed = embeds.make_embed(context=ctx, title="Reminder deleted", 
            description=f"Reminder ID: {reminder_id} has been deleted.",
            image_url=config.remind_red, color=config.soft_red)
        await ctx.send(embed=embed)

def setup(bot: Bot) -> None:
    """ Load the Reminder cog. """
    bot.add_cog(Reminder(bot))
    log.info("Cog loaded: reminder")
