import logging
import time
from datetime import datetime

import discord
from discord.ext import commands
from discord.commands import Option, context, permissions, slash_command

from utils import database, embeds
from utils.config import config
from utils.pagination import LinePaginator


log = logging.getLogger(__name__)


class NoteCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="addnote", guild_ids=config["guild_ids"], default_permission=False)
    @permissions.has_role(config["roles"]["staff"])
    async def add_note(
        self,
        ctx: context.ApplicationContext,
        user: Option(discord.Member, description="The user to add the note to", required=True),
        note: Option(str, description="The note to leave on the user", required=True),
    ):
        """Adds a moderator note to a user."""
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if not isinstance(user, discord.Member):
            user = await self.bot.fetch_user(user)

        # Open a connection to the database.
        db = database.Database().get()

        # Add the note to the mod_logs database.
        note_id = db["mod_logs"].insert(
            dict(
                user_id=user.id,
                mod_id=ctx.author.id,
                timestamp=int(time.time()),
                reason=note,
                type="note",
            )
        )

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Noting user: {user.name}",
            description=f"{user.mention} was noted by {ctx.author.mention}",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color="blurple",
        )
        embed.add_field(name="ID: ", value=note_id, inline=False)
        embed.add_field(name="Note: ", value=note, inline=False)
        await ctx.send(embed=embed)

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

    @slash_command(name="search", guild_ids=config["guild_ids"], default_permission=False)
    @permissions.has_role(config["roles"]["staff"])
    async def search_mod_actions(
        self,
        ctx: context.ApplicationContext,
        user: Option(discord.User, description="The user to lookup", required=True),
        action: Option(
            str,
            description="Filter specific actions",
            choices=["ban", "unban", "mute", "unmute", "kick", "restrict", "unrestrict", "warn", "note"],
            required=False
        )
    ):
        """Searches for mod actions on a user"""
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if not isinstance(user, discord.Member):
            user = await self.bot.fetch_user(user)

        # Open a connection to the database.
        db = database.Database().get()

        # Querying DB for the list of actions matching the filter criteria (if mentioned).
        if action:
            results = db["mod_logs"].find(user_id=user.id, type=action, order_by="-id")
        else:
            results = db["mod_logs"].find(user_id=user.id, order_by="-id")

        # Creating a List to store actions for the paginator.
        actions = []
        for action in results:
            action_emoji = {
                "mute": "🤐",
                "unmute": "🗣",
                "warn": "⚠",
                "kick": "👢",
                "ban": "🔨",
                "unban": "⚒",
                "restrict": "🚫",
                "unrestrict": "✅",
                "note": "🗒️",
            }

            action_type = action["type"]
            # Capitalising the first letter of the action type.
            action_type = action_type[0].upper() + action_type[1:]
            # Adding fluff emoji to action_type.
            action_type = f"{action_emoji[action['type']]} {action_type}"

            actions.append(
                f"""**{action_type}**
                **ID:** {action['id']}
                **Timestamp:** {datetime.fromtimestamp(action['timestamp'])} UTC
                **Moderator:** <@!{action['mod_id']}>
                **Reason:** {action['reason']}"""
            )

        if not actions:
            return await embeds.error_message(
                ctx=ctx,
                description="No mod actions found for that user!"
            )

        db.close()

        embed = embeds.make_embed(title="Mod Actions")
        embed.set_author(name=user, icon_url=user.avatar)

        # paginating through the results
        await LinePaginator.paginate(
            lines=actions,
            ctx=ctx,
            embed=embed,
            max_lines=4,
            max_size=2000,
            linesep="\n",
            timeout=120,
        )

    @slash_command(name="editlog", guild_ids=config["guild_ids"], default_permission=False)
    @permissions.has_role(config["roles"]["staff"])
    async def edit_log(
        self,
        ctx: context.ApplicationContext,
        id: Option(int, description="The ID of the log or note to be edited", required=True),
        note: Option(str, description="The updated message for the log or note", required=True),
    ):
        await ctx.defer()

        # Open a connection to the database.
        db = database.Database().get()

        table = db["mod_logs"]

        mod_log = table.find_one(id=id)
        if not mod_log:
            await embeds.error_message(
                ctx=ctx, description="Could not find a log with that ID!"
            )
            return

        user = await self.bot.fetch_user(mod_log["user_id"])
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Edited log: {user.name}",
            description=f"Log #{id} for {user.mention} was updated by {ctx.author.mention}",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color="soft_green",
        )
        embed.add_field(name="Before:", value=mod_log["reason"], inline=False)
        embed.add_field(name="After:", value=note, inline=False)
        await ctx.send(embed=embed)

        mod_log["reason"] = note
        table.update(mod_log, ["id"])

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(NoteCommands(bot))
    log.info("Commands loaded: note")
