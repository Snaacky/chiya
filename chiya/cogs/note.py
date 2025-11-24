from typing import Literal

import arrow
import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from chiya import db
from chiya.config import config
from chiya.models import ModLog
from chiya.utils import embeds
from chiya.utils.helpers import log_embed_to_channel
from chiya.utils.pagination import MyMenuPages, MySource


class NoteCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="addnote", description="Add a note to the users profile")
    @app_commands.guilds(config.guild_id)
    @app_commands.describe(user="The user to add the note to")
    @app_commands.describe(note="The note to leave on the user")
    async def add_note(self, ctx: discord.Interaction, user: discord.User | discord.Member, note: str) -> None:
        """Adds a note to the specified user queryable via /search."""
        await ctx.response.defer(thinking=True, ephemeral=True)

        log = ModLog()
        log.user_id = user.id
        log.mod_id = ctx.user.id
        log.timestamp = arrow.utcnow().int_timestamp
        log.reason = note
        log.type = "note"

        db.session.add(log)
        db.session.commit()

        embed = discord.Embed()
        embed.title = f"Noting user: {user.name}"
        embed.description = f"{user.mention} was noted by {ctx.user.mention}"
        embed.color = discord.Color.blurple()
        embed.add_field(name="ID:", value=log.id, inline=False)
        embed.add_field(name="Note:", value=log.reason, inline=False)
        embed.set_thumbnail(url="https://i.imgur.com/A4c19BJ.png")

        await ctx.followup.send(embed=embed)
        await log_embed_to_channel(ctx=ctx, embed=embed)

    @app_commands.command(name="search", description="Search through a users notes and mod logs")
    @app_commands.guilds(config.guild_id)
    @app_commands.describe(user="The user to lookup")
    @app_commands.describe(action="Filter specific actions")
    async def search_mod_actions(
        self,
        ctx: discord.Interaction,
        user: discord.User | discord.Member,
        action: Literal["ban", "unban", "mute", "unmute", "warn", "note"] | None = None,
    ) -> None:
        """
        Search for the mod actions and notes for a user. The search can be
        filtered by ban, unban, unmute, warn, or notes. Users are not alerted
        when they have a /search command ran on them.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if action:
            results = db.session.scalars(
                select(ModLog).where(ModLog.user_id == user.id, ModLog.type == action).order_by(ModLog.id.asc())
            )
        else:
            results = db.session.scalars(select(ModLog).where(ModLog.user_id == user.id).order_by(ModLog.id.asc()))

        actions = []
        for result in results:
            action_emoji = {
                "mute": "🤐",
                "unmute": "🗣",
                "warn": "⚠",
                "ban": "🔨",
                "unban": "⚒",
                "note": "🗒️",
            }

            action_string = f"""**{action_emoji[result.type]} {result.type.title()}**
                **ID:** {result.id}
                **Timestamp:** {arrow.get(result.timestamp)} UTC
                **Moderator:** <@!{result.mod_id}>
                **Reason:** {result.reason}"""

            if result.type == "mute":
                action_string += f"\n**Duration:** {result.duration}"

            actions.append(action_string)

        if not actions:
            return await embeds.send_error(ctx=ctx, description="No mod actions found for that user!")

        embed = discord.Embed()
        embed.title = "Mod Actions"
        embed.set_author(name=user, icon_url=user.display_avatar)

        formatter = MySource(actions, embed)
        menu = MyMenuPages(formatter)
        await menu.start(ctx)

    @app_commands.command(name="editlog", description="Edit a user's notes and mod logs")
    @app_commands.guilds(config.guild_id)
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

        log = db.session.scalar(select(ModLog).where(ModLog.id == id))
        if not log:
            return await embeds.send_error(ctx=ctx, description="Could not find a log with that ID!")

        log.reason = note
        db.session.commit()

        user = await self.bot.fetch_user(log.user_id)

        embed = discord.Embed()
        embed.title = f"Edited log: {user.name}"
        embed.description = f"Log #{id} for {user.mention} was updated by {ctx.user.mention}"
        embed.color = discord.Color.green()
        embed.add_field(name="Before:", value=log.reason, inline=False)
        embed.add_field(name="After:", value=note, inline=False)
        embed.set_thumbnail(url="https://i.imgur.com/A4c19BJ.png")

        await ctx.followup.send(embed=embed)
        await log_embed_to_channel(ctx=ctx, embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NoteCog(bot))
