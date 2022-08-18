import logging
import time
from datetime import datetime
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from chiya import config, database
from chiya.utils import embeds
from chiya.utils.pagination import LinePaginator


log = logging.getLogger(__name__)


class NoteCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="addnote", description="Add a note to the users profile")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.checks.has_role(config["roles"]["staff"])
    @app_commands.describe(user="The user to add the note to")
    @app_commands.describe(note="The note to leave on the user")
    async def add_note(self, ctx: discord.Interaction, user: discord.Member | discord.User, note: str) -> None:
        """
        Adds a note to the users profile.

        Notes can only be seen by staff via the /search command and do not
        punish the user in anyway. They are merely for staff to log relevant
        information. Users are not alerted when a note is added to them.
        """
        await ctx.response.defer(thinking=True)

        db = database.Database().get()
        note_id = db["mod_logs"].insert(
            dict(
                user_id=user.id,
                mod_id=ctx.user.id,
                timestamp=int(time.time()),
                reason=note,
                type="note",
            )
        )
        db.commit()
        db.close()

        embed = embeds.make_embed(
            title=f"Noting user: {user.name}",
            description=f"{user.mention} was noted by {ctx.user.mention}",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color=discord.Color.blurple(),
            fields=[
                {"name": "ID:", "value": note_id, "inline": False},
                {"name": "Note:", "value": note, "inline": False},
            ],
        )

        await ctx.followup.send(embed=embed)

    @app_commands.command(name="search", description="Search through a users notes and mod logs")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.checks.has_role(config["roles"]["staff"])
    @app_commands.describe(user="The user to lookup")
    @app_commands.describe(action="Filter specific actions")
    async def search_mod_actions(
        self,
        ctx: discord.Interaction,
        user: discord.Member | discord.User,
        action: Literal["ban", "unban", "mute", "unmute", "warn", "note"] = None
    ) -> None:
        """
        Search for the mod actions and notes for a user. The search can be
        filtered by ban, unban, unmute, warn, or notes.

        Users are not alerted when they have a /search command ran on them.
        Only the command invoking user can change pages on the pagination.
        It is imperative that the command is not ran in public channels
        because the output is not hidden.

        TODO: Bug that occurs when running /search:
            Traceback (most recent call last):
            File "virtualenvs\\chiya-Z7ITmrUJ-py3.10\\lib\\site-packages\\sqlalchemy\\engine\\base.py", line 1995, in _safe_close_cursor
                cursor.close()
            File "virtualenvs\\chiya-Z7ITmrUJ-py3.10\\lib\\site-packages\\MySQLdb\\cursors.py", line 83, in close
                while self.nextset():
            File "virtualenvs\\chiya-Z7ITmrUJ-py3.10\\lib\\site-packages\\MySQLdb\\\cursors.py", line 137, in nextset
                nr = db.next_result()
            MySQLdb.OperationalError: (2006, '')
        """
        await ctx.response.defer(thinking=True)

        db = database.Database().get()
        # TODO: can't this be merged into one call because action will return None either way?
        if action:
            results = db["mod_logs"].find(user_id=user.id, type=action, order_by="-id")
        else:
            results = db["mod_logs"].find(user_id=user.id, order_by="-id")
        db.close()

        actions = []
        for action in results:
            action_emoji = {
                "mute": "🤐",
                "unmute": "🗣",
                "warn": "⚠",
                "ban": "🔨",
                "unban": "⚒",
                "note": "🗒️",
            }

            action_type = action["type"]
            action_type = action_type[0].upper() + action_type[1:]
            action_type = f"{action_emoji[action['type']]} {action_type}"

            action_string = f"""**{action_type}**
                **ID:** {action["id"]}
                **Timestamp:** {datetime.fromtimestamp(action["timestamp"])} UTC
                **Moderator:** <@!{action["mod_id"]}>
                **Reason:** {action["reason"]}"""

            if action["type"] == "mute":
                action_string += f"\n**Duration:** {action['duration']}"

            actions.append(action_string)

        if not actions:
            return await embeds.error_message(ctx=ctx, description="No mod actions found for that user!")

        embed = embeds.make_embed(title="Mod Actions")
        embed.set_author(name=user, icon_url=user.display_avatar)

        await LinePaginator.paginate(
            lines=actions,
            ctx=ctx,
            embed=embed,
            max_lines=4,
            max_size=2000,
            linesep="\n",
            timeout=120,
        )

    @app_commands.command(name="editlog", description="Edit a user's notes and mod logs")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.checks.has_role(config["roles"]["staff"])
    @app_commands.describe(id="The ID of the log or note to be edited")
    @app_commands.describe(note="The updated message for the log or note")
    async def edit_log(self, ctx: discord.Interaction, id: int, note: str) -> None:
        """
        Edit a mod action or note on a users /search history.

        This is a destructive action and will only change the original user
        note. It should primarily be used for adding additional details
        and correct English errors.

        A history of edits is not maintained and will only show the
        latest edited message.
        """
        # TODO: Add some sort of support for history or editing mods.
        await ctx.response.defer(thinking=True)

        db = database.Database().get()
        mod_log = db["mod_logs"].find_one(id=id)
        if not mod_log:
            return await embeds.error_message(ctx=ctx, description="Could not find a log with that ID!")

        user = await self.bot.fetch_user(mod_log["user_id"])
        embed = embeds.make_embed(
            title=f"Edited log: {user.name}",
            description=f"Log #{id} for {user.mention} was updated by {ctx.user.mention}",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color=discord.Color.green(),
            fields=[
                {"name": "Before:", "value": mod_log["reason"], "inline": False},
                {"name": "After:", "value": note, "inline": False},
            ],
        )

        mod_log["reason"] = note
        db["mod_logs"].update(mod_log, ["id"])
        db.commit()
        db.close()

        await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NoteCommands(bot))
    log.info("Commands loaded: note")
