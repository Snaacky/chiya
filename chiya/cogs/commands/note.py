import time
from datetime import datetime
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger as log

from chiya import database
from chiya.config import config
from chiya.utils import embeds
from chiya.utils.helpers import log_embed_to_channel
from chiya.utils.pagination import MyMenuPages, MySource


class NoteCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="addnote", description="Add a note to the users profile")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.describe(user="The user to add the note to")
    @app_commands.describe(note="The note to leave on the user")
    async def add_note(self, ctx: discord.Interaction, user: discord.Member | discord.User, note: str) -> None:
        """Adds a note to the specified user queryable via /search."""
        await ctx.response.defer(thinking=True, ephemeral=True)

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
        await log_embed_to_channel(ctx=ctx, embed=embed)

    @app_commands.command(name="search", description="Search through a users notes and mod logs")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.describe(user="The user to lookup")
    @app_commands.describe(action="Filter specific actions")
    async def search_mod_actions(
        self,
        ctx: discord.Interaction,
        user: discord.Member | discord.User,
        action: Literal["ban", "unban", "mute", "unmute", "warn", "note"] = None,
    ) -> None:
        """
        Search for the mod actions and notes for a user. The search can be
        filtered by ban, unban, unmute, warn, or notes. Users are not alerted
        when they have a /search command ran on them.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        db = database.Database().get()
        # TODO: can't this be merged into one call because action will return None either way?
        if action:
            results = db["mod_logs"].find(user_id=user.id, type=action, order_by="-id")
        else:
            results = db["mod_logs"].find(user_id=user.id, order_by="-id")

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

            action_string = f"""**{action_emoji[action['type']]} {action['type'][0].title()}**
                **ID:** {action["id"]}
                **Timestamp:** {datetime.fromtimestamp(action["timestamp"])} UTC
                **Moderator:** <@!{action["mod_id"]}>
                **Reason:** {action["reason"]}"""

            if action["type"] == "mute":
                action_string += f"\n**Duration:** {action['duration']}"

            actions.append(action_string)

        db.close()
        if not actions:
            return await embeds.error_message(ctx=ctx, description="No mod actions found for that user!")

        embed = embeds.make_embed(title="Mod Actions")
        embed.set_author(name=user, icon_url=user.display_avatar)

        formatter = MySource(actions, embed)
        menu = MyMenuPages(formatter)
        await menu.start(ctx)

    @app_commands.command(name="editlog", description="Edit a user's notes and mod logs")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
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
        await ctx.response.defer(thinking=True, ephemeral=True)

        db = database.Database().get()
        log = db["mod_logs"].find_one(id=id)
        if not log:
            return await embeds.error_message(ctx=ctx, description="Could not find a log with that ID!")

        user = await self.bot.fetch_user(log["user_id"])
        embed = embeds.make_embed(
            title=f"Edited log: {user.name}",
            description=f"Log #{id} for {user.mention} was updated by {ctx.user.mention}",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color=discord.Color.green(),
            fields=[
                {"name": "Before:", "value": log["reason"], "inline": False},
                {"name": "After:", "value": note, "inline": False},
            ],
        )

        log["reason"] = note
        db["mod_logs"].update(log, ["id"])
        db.commit()
        db.close()

        await ctx.followup.send(embed=embed)
        await log_embed_to_channel(ctx=ctx, embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NoteCommands(bot))
    log.info("Commands loaded: note")
