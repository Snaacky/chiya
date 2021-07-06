import asyncio
import datetime
import logging
import time

import dataset
import discord
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_permission
from discord_slash.model import SlashCommandPermissionType

import config
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
        guild_ids=[config.guild_id],
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
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
                create_permission(config.role_trial_mod, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def add_note(self, ctx: SlashContext, user: discord.User, note: str):
        """ Adds a moderator note to a user. """
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        embed = embeds.make_embed(
            ctx=ctx, 
            title=f"Noting user: {user.name}", 
            description=f"{user.mention} was noted by {ctx.author.mention}: {note}",
            thumbnail_url=config.pencil, 
            color="blurple"
        )
        await ctx.send(embed=embed)

        # Add the note to the mod_logs database.
        with dataset.connect(database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=note, type="note"
            ))
    
    @cog_ext.cog_slash(
        name="search", 
        description="View users notes and mod actions history",
        guild_ids=[config.guild_id],
        options=[
            create_option(
                name="user",
                description="The user to lookup",
                option_type=6,
                required=True
            ),
            create_option(
                name="action",
                description="Filter specific actions (warns, kicks, mutes, bans, etc.)",
                option_type=3,
                required=False
            ),
        ],
        default_permission=False,
        permissions={
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
                create_permission(config.role_trial_mod, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def search_mod_actions(self, ctx: Context, user: discord.User, action_type: str = None):
        """ Searches for mod actions on a user """
        await ctx.defer()

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        result = None
        # querying DB for the list of actions matching the filter criteria (if mentioned)
        with dataset.connect(database.get_db()) as db:
            mod_logs = db["mod_logs"]
            if action_type is not None:
                # Remove plurality from action_type to try and autocorrect for the user. 
                if action_type[-1] == "s":
                    action_type = action_type[:-1]
                result = mod_logs.find(user_id=user.id, type=action_type.lower())
            else:
                result = mod_logs.find(user_id=user.id)

        # creating a list to store actions for the paginator
        actions = []
        page_no = 0
        # number of results per page
        per_page = 4    
        # creating a temporary list to store the per_page number of actions
        page = []
        
        for x in result:
            # appending dict of action to the particular page
            page.append(dict(
                id=x['id'],
                user_id=x['user_id'],
                mod_id=x['mod_id'],
                reason=x['reason'],
                type=x['type'],
                timestamp = x['timestamp']
            ).copy())
            
            if (page_no + 1) % per_page == 0 and page_no != 0:
                # appending the current page to the main actions list and resetting the page
                actions.append(page.copy())
                page = []
            
            # incrementing the counter variable
            page_no += 1
        
        if not (page_no + 1) % per_page == 0 and len(page) != 0:
            # for the situations when some pages were left behind
            actions.append(page.copy())
        
        if not actions:
            # nothing was found, so returning an appropriate error.
            await embeds.error_message(ctx=ctx, description="No mod actions found for that user!")
            return

        page_no = 0

        def get_page(action_list, user, page_no: int) -> Embed:
            embed = embeds.make_embed(title="Mod Actions", description=f"Page {page_no+1} of {len(action_list)}")
            embed.set_author(name=user, icon_url=user.avatar_url)
            action_emoji = dict(
                mute = "🤐",
                unmute = "🗣",
                warn = "⚠",
                kick = "👢",
                ban = "🔨",
                unban = "⚒",
                note = "🗒️"
            )
            for action in action_list[page_no]:
                action_type = action["type"]
                # capitalising the first letter of the action type
                action_type = action_type[0].upper() + action_type[1:]
                # Adding fluff emoji to action_type
                action_type = f"{action_emoji[action['type']]} {action_type}"
                # Appending the other data about the action
                value = f"""
                **Timestamp:** {str(datetime.datetime.fromtimestamp(action['timestamp'], tz=datetime.timezone.utc)).replace("+00:00", " UTC")} 
                **Moderator:** <@!{action['mod_id']}>
                **Reason:** {action['reason']}
                """
                embed.add_field(name=f"{action_type} | ID: {action['id']}", value=value, inline=False)
                
            return embed
        
        # sending the first page. We'll edit this during pagination.
        msg = await ctx.send(embed=get_page(action_list=actions, user=user, page_no=page_no))

        FIRST_EMOJI = "\u23EE"   # [:track_previous:]
        LEFT_EMOJI = "\u2B05"    # [:arrow_left:]
        RIGHT_EMOJI = "\u27A1"   # [:arrow_right:]
        LAST_EMOJI = "\u23ED"    # [:track_next:]
        DELETE_EMOJI = "⛔"  # [:trashcan:]
        SAVE_EMOJI = "💾"  # [:floppy_disk:]

        bot = ctx.bot
        timeout = 30

        PAGINATION_EMOJI = (FIRST_EMOJI, LEFT_EMOJI, RIGHT_EMOJI,
                            LAST_EMOJI, DELETE_EMOJI, SAVE_EMOJI)

        
        for x in PAGINATION_EMOJI:
            await msg.add_reaction(x)

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            if reaction.emoji in PAGINATION_EMOJI and user == ctx.author:
                return True
            return False

        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=timeout, check=check)
            except asyncio.TimeoutError:
                await msg.delete()
                break

            if str(reaction.emoji) == DELETE_EMOJI:
                await msg.delete()
                break

            if str(reaction.emoji) == SAVE_EMOJI:
                await msg.clear_reactions()
                break

            if reaction.emoji == FIRST_EMOJI:
                await msg.remove_reaction(reaction.emoji, user)
                page_no = 0

            if reaction.emoji == LAST_EMOJI:
                await msg.remove_reaction(reaction.emoji, user)
                page_no = len(actions) - 1

            if reaction.emoji == LEFT_EMOJI:
                await msg.remove_reaction(reaction.emoji, user)

                if page_no <= 0:
                    page_no = len(actions) - 1
                else:
                    page_no -= 1

            if reaction.emoji == RIGHT_EMOJI:
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
        guild_ids=[config.guild_id],
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
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
                create_permission(config.role_trial_mod, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def edit_log(self, ctx: SlashContext, id: int, reason: str):
        await ctx.defer()
        
        with dataset.connect(database.get_db()) as db:
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
            thumbnail_url=config.pencil, 
            color="soft_green"
        )
        embed.add_field(name="Before:", value=mod_log["reason"], inline=False)
        embed.add_field(name="After:", value=reason, inline=False)
        await ctx.send(embed=embed)

        mod_log["reason"] = reason
        table.update(mod_log, ["id"])

def setup(bot: Bot) -> None:
    """ Load the Notes cog. """
    bot.add_cog(NotesCog(bot))
    log.info("Commands loaded: notes")
