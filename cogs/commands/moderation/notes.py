import asyncio
import datetime
import logging
import time

import dataset
import discord
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from cogs.commands import settings
from utils import database
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class NotesCog(Cog):
    """ Notes Cog """

    def __init__(self, bot):
        self.bot = bot

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="addnote",
        description="Add a note to a user",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="user",
                description="The user to add the note to",
                option_type=6,
                required=True
            ),
            create_option(
                name="note",
                description="The note to leave on the user",
                option_type=3,
                required=True
            ),
        ],
        default_permission=False,
        permissions={
            settings.get_value("guild_id"): [
                create_permission(settings.get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
                create_permission(settings.get_value("role_trial_mod"), SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def add_note(self, ctx: SlashContext, user: discord.User, note: str):
        """ Adds a moderator note to a user. """
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if not isinstance(user, discord.Member):
            user = await self.bot.fetch_user(user)

        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        # Add the note to the mod_logs database.
        note_id = db["mod_logs"].insert(dict(
            user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=note, type="note"
        ))

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Noting user: {user.name}",
            description=f"{user.mention} was noted by {ctx.author.mention}",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color="blurple"
        )
        embed.add_field(name="ID: ", value=note_id, inline=False)
        embed.add_field(name="Note: ", value=note, inline=False)
        await ctx.send(embed=embed)

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

    @cog_ext.cog_slash(
        name="search",
        description="View users notes and mod actions history",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="user",
                description="The user to lookup",
                option_type=6,
                required=True
            ),
            create_option(
                name="action",
                description="Filter specific actions (ban, unban, mute, unmute, warn, kick)",
                option_type=3,
                required=False
            ),
        ],
        default_permission=False,
        permissions={
            settings.get_value("guild_id"): [
                create_permission(settings.get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
                create_permission(settings.get_value("role_trial_mod"), SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def search_mod_actions(self, ctx: SlashContext, user: discord.User, action: str = None):
        """ Searches for mod actions on a user """
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if not isinstance(user, discord.Member):
            user = await self.bot.fetch_user(user)

        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        # Querying DB for the list of actions matching the filter criteria (if mentioned).
        mod_logs = db["mod_logs"]
        options = ["ban", "unban", "mute", "unmute", "restrict", "unrestrict", "warn", "kick", "note"]
        if action:
            # Attempt to check for the plural form of the options and strip it.
            if action[-1] == "s":
                action = action[:-1]
            if any(action == option for option in options):
                results = mod_logs.find(user_id=user.id, type=action.lower())
            else:
                await embeds.error_message(
                    ctx=ctx,
                    description=f"\"{action}\" is not a valid mod action filter. \n\nValid filters: ban, unban, mute, unmute, restrict, unrestrict, warn, kick, note"
                )
                # Close the connection.
                db.close()
                return
        else:
            results = mod_logs.find(user_id=user.id)

        # Creating a list to store actions for the paginator.
        actions = []
        page_no = 0
        # Number of results per page.
        per_page = 4
        # Creating a temporary list to store the per_page number of actions.
        page = []

        for entry in results:
            # Appending dict of action to the particular page.
            page.append(dict(
                id=entry["id"],
                user_id=entry["user_id"],
                mod_id=entry["mod_id"],
                reason=entry["reason"],
                type=entry["type"],
                timestamp=entry["timestamp"]
            ).copy())

            if (page_no + 1) % per_page == 0 and page_no != 0:
                # Appending the current page to the main actions list and resetting the page.
                actions.append(page.copy())
                page = []

            # Incrementing the counter variable.
            page_no += 1

        if not (page_no + 1) % per_page == 0 and len(page) != 0:
            # For the situations when some pages were left behind.
            actions.append(page.copy())

        if not actions:
            # Nothing was found, so returning an appropriate error.
            await embeds.error_message(ctx=ctx, description="No mod actions found for that user!")
            return

        page_no = 0

        # Close the connection.
        db.close()

        def get_page(action_list, user, page_no: int) -> Embed:
            embed = embeds.make_embed(title="Mod Actions", description=f"Page {page_no + 1} of {len(action_list)}")
            embed.set_author(name=user, icon_url=user.avatar_url)
            action_emoji = dict(
                mute="🤐",
                unmute="🗣",
                warn="⚠",
                kick="👢",
                ban="🔨",
                unban="⚒",
                restrict="🚫",
                unrestrict="✅",
                note="🗒️"
            )
            for action in action_list[page_no]:
                action_type = action["type"]
                # Capitalising the first letter of the action type.
                action_type = action_type[0].upper() + action_type[1:]
                # Adding fluff emoji to action_type.
                action_type = f"{action_emoji[action['type']]} {action_type}"
                # Appending the other data about the action.
                value = f"""
                **Timestamp:** {str(datetime.datetime.fromtimestamp(action['timestamp'], tz=datetime.timezone.utc)).replace("+00:00", " UTC")} 
                **Moderator:** <@!{action['mod_id']}>
                **Reason:** {action['reason']}
                """
                embed.add_field(name=f"{action_type} | ID: {action['id']}", value=value, inline=False)

            return embed

        # Sending the first page. We'll edit this during pagination.
        msg = await ctx.send(embed=get_page(action_list=actions, user=user, page_no=page_no))

        first_emoji = "\u23EE"  # [:track_previous:]
        left_emoji = "\u2B05"  # [:arrow_left:]
        right_emoji = "\u27A1"  # [:arrow_right:]
        last_emoji = "\u23ED"  # [:track_next:]
        delete_emoji = "⛔"  # [:trashcan:]
        save_emoji = "💾"  # [:floppy_disk:]

        bot = ctx.bot
        timeout = 30

        pagination_emoji = (first_emoji, left_emoji, right_emoji,
                            last_emoji, delete_emoji, save_emoji)

        for x in pagination_emoji:
            await msg.add_reaction(x)

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            if reaction.emoji in pagination_emoji and user == ctx.author:
                return True
            return False

        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=timeout, check=check)
            except asyncio.TimeoutError:
                await msg.delete()
                break

            if str(reaction.emoji) == delete_emoji:
                await msg.delete()
                break

            if str(reaction.emoji) == save_emoji:
                await msg.clear_reactions()
                break

            if reaction.emoji == first_emoji:
                await msg.remove_reaction(reaction.emoji, user)
                page_no = 0

            if reaction.emoji == last_emoji:
                await msg.remove_reaction(reaction.emoji, user)
                page_no = len(actions) - 1

            if reaction.emoji == left_emoji:
                await msg.remove_reaction(reaction.emoji, user)

                if page_no <= 0:
                    page_no = len(actions) - 1
                else:
                    page_no -= 1

            if reaction.emoji == right_emoji:
                await msg.remove_reaction(reaction.emoji, user)

                if page_no >= len(actions) - 1:
                    page_no = 0
                else:
                    page_no += 1

            embed = get_page(action_list=actions, user=user, page_no=page_no)

            if embed is not None:
                await msg.edit(embed=embed)

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="editlog",
        description="Edits an existing log or note for a user",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="id",
                description="The ID of the log or note to be edited",
                option_type=4,
                required=True
            ),
            create_option(
                name="note",
                description="The updated message for the log or note",
                option_type=3,
                required=True
            ),
        ],
        default_permission=False,
        permissions={
            settings.get_value("guild_id"): [
                create_permission(settings.get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
                create_permission(settings.get_value("role_trial_mod"), SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def edit_log(self, ctx: SlashContext, id: int, note: str):
        await ctx.defer()

        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        table = db["mod_logs"]

        mod_log = table.find_one(id=id)
        if not mod_log:
            await embeds.error_message(ctx=ctx, description="Could not find a log with that ID!")
            return

        user = await self.bot.fetch_user(mod_log["user_id"])
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Edited log: {user.name}",
            description=f"Log #{id} for {user.mention} was updated by {ctx.author.mention}",
            thumbnail_url="https://i.imgur.com/A4c19BJ.png",
            color="soft_green"
        )
        embed.add_field(name="Before:", value=mod_log["reason"], inline=False)
        embed.add_field(name="After:", value=note, inline=False)
        await ctx.send(embed=embed)

        mod_log["reason"] = note
        table.update(mod_log, ["id"])

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """ Load the Notes cog. """
    bot.add_cog(NotesCog(bot))
    log.info("Commands loaded: notes")
