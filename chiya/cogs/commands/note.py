import logging
import time
from datetime import datetime

import discord
from discord.commands import Option, context, slash_command
from discord.ext import commands

from chiya import config, database
from chiya.utils import embeds
from chiya.utils.pagination import LinePaginator


log = logging.getLogger(__name__)


class NoteCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @slash_command(name="addnote", guild_ids=config["guild_ids"])
    @commands.has_role(config["roles"]["staff"])
    async def add_note(
        self,
        ctx: context.ApplicationContext,
        user: Option(discord.User, description="The user to add the note to", required=True),
        note: Option(str, description="The note to leave on the user", required=True),
    ) -> None:
        """
        Adds a note to the users profile.

        Notes can only be seen by staff via the /search command and do not
        punish the user in anyway. They are merely for staff to log relevant
        information. Users are not alerted when a note is added to them.
        """
        await ctx.defer()

        if not isinstance(user, discord.Member):
            user = await self.bot.fetch_user(user)

        db = database.Database().get()
        note_id = db["mod_logs"].insert(
            dict(
                user_id=user.id,
                mod_id=ctx.author.id,
                timestamp=int(time.time()),
                reason=note,
                type="note",
            )
        )
        db.commit()
        db.close()

        embed = embeds.make_embed(
            title=f"Noting user: {user.name}",
            description=f"{user.mention} was noted by {ctx.author.mention}",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color=discord.Color.blurple(),
            fields=[
                {"name": "ID:", "value": note_id, "inline": False},
                {"name": "Note:", "value": note, "inline": False},
            ],
        )

        await ctx.send_followup(embed=embed)

    @slash_command(name="search", guild_ids=config["guild_ids"])
    @commands.has_role(config["roles"]["staff"])
    async def search_mod_actions(
        self,
        ctx: context.ApplicationContext,
        user: Option(discord.User, description="The user to lookup", required=True),
        action: Option(
            str,
            description="Filter specific actions",
            choices=["ban", "unban", "mute", "unmute", "warn", "note"],
            required=False,
        ),
    ) -> None:
        """
        Search for the mod actions and notes for a user. The search can be
        filtered by ban, unban, unmute, warn, or notes.

        Users are not alerted when they have a /search command ran on them.
        Only the command invoking user can change pages on the pagination.
        It is imperative that the command is not ran in public channels
        because the output is not hidden.
        """
        await ctx.defer()

        if not isinstance(user, discord.Member):
            user = await self.bot.fetch_user(user.id)

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

    @slash_command(name="editlog", guild_ids=config["guild_ids"])
    @commands.has_role(config["roles"]["staff"])
    async def edit_log(
        self,
        ctx: context.ApplicationContext,
        id: Option(int, description="The ID of the log or note to be edited", required=True),
        note: Option(str, description="The updated message for the log or note", required=True),
    ) -> None:
        """
        Edit a mod action or note on a users /search history.

        This is a destructive action and will only change the original user
        note. It should primarily be used for adding additional details
        and correct English errors.

        A history of edits is not maintained and will only show the
        latest edited message.
        """
        # TODO: Add some sort of support for history or editing mods.
        await ctx.defer()

        db = database.Database().get()
        mod_log = db["mod_logs"].find_one(id=id)
        if not mod_log:
            return await embeds.error_message(ctx=ctx, description="Could not find a log with that ID!")

        user = await self.bot.fetch_user(mod_log["user_id"])
        embed = embeds.make_embed(
            title=f"Edited log: {user.name}",
            description=f"Log #{id} for {user.mention} was updated by {ctx.author.mention}",
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

        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(NoteCommands(bot))
    log.info("Commands loaded: note")
