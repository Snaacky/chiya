import datetime
import logging
import time

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, Greedy

import config
import utils.database
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class ModerationCog(Cog):
    """ Moderation Cog """

    def __init__(self, bot):
        self.bot = bot

    async def can_action_member(self, ctx: Context, member: discord.Member) -> bool:
        """ Stop mods from doing stupid things. """
        # Stop mods from actioning on the bot.
        if member.id == self.bot.user.id:
            await ctx.reply("You cannot action that member.")
            return False

        # Stop mods from actioning one another, people higher ranked than them or themselves.
        if member.top_role >= ctx.author.top_role:
            await ctx.reply("You cannot action that member.")
            return False

        # Checking if Bot is able to even perform the action
        if member.top_role >= member.guild.me.top_role:
            await ctx.reply("Bot is inferior or equal to that member, thus does not have permission to take action.")
            return False

        # Otherwise, the action is probably valid, return true.
        return True

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(ban_members=True, send_messages=True, embed_links=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="ban")
    async def ban_member(self, ctx: Context, user: discord.User, *, reason: str):
        """ Bans user from guild. """

        # Checking if user is in guild.
        if ctx.guild.get_member(user.id) is not None:
            # Convert to member object
            member = await commands.MemberConverter().convert(ctx, user.mention)
            # Checks if invoker can action that member (self, bot, etc.)
            if not await self.can_action_member(ctx, member):
                return

        embed = embeds.make_embed(context=ctx, title=f"Banning user: {user.name}",
                                  image_url=config.user_ban, color=config.soft_red)
        embed.description = f"{user.mention} was banned by {ctx.author.mention} for:\n{reason}"

        # Send user message telling them that they were banned and why.
        try:  # Incase user has DM's Blocked.
            channel = await user.create_dm()
            message = f"You were banned from {ctx.guild} for: {reason}"
            await channel.send(message)
        except:
            embed.add_field(
                name="NOTICE", value="Unable to message user about this action.")

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.ban
        await ctx.guild.ban(user=user, reason=reason, delete_message_days=0)

        # Add the ban to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="ban"
            ))

        await ctx.reply(embed=embed)

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(ban_members=True, send_messages=True, embed_links=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="unban")
    async def unban_member(self, ctx: Context, user: discord.User, *, reason: str):
        """ Unbans user from guild. """

        embed = embeds.make_embed(context=ctx, title=f"Unbanning user: {user.name}",
                                  image_url=config.user_unban, color=config.soft_green)
        embed.description = f"{user.mention} was unbanned by {ctx.author.mention} for:\n{reason}"

        # Send user message telling them that they were unbanned and why.
        try:  # Incase user has DM's Blocked.
            channel = await user.create_dm()
            message = f"You were unbanned from {ctx.guild} for: {reason}"
            await channel.send(message)
        except:
            embed.add_field(
                name="NOTICE", value="Unable to message member about this action.")

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.unban
        await ctx.guild.unban(user=user, reason=reason)

        # Add the unban to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="unban"
            ))

        await ctx.reply(embed=embed)

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(kick_members=True, send_messages=True, embed_links=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="kick")
    async def kick_member(self, ctx: Context, member: discord.Member, *, reason: str):
        """ Kicks member from guild. """

        # Checks if invoker can action that member (self, bot, etc.)
        if not await self.can_action_member(ctx, member):
            return

        embed = embeds.make_embed(context=ctx, title=f"Kicking member: {member.name}",
                                  image_url=config.user_ban, color=config.soft_red)
        embed.description = f"{member.mention} was kicked by {ctx.author.mention} for:\n{reason}"

        # Send user message telling them that they were kicked and why.
        try:  # Incase user has DM's Blocked.
            channel = await member.create_dm()
            message = f"You were kicked from {ctx.guild} for: {reason}"
            await channel.send(message)
        except:
            embed.add_field(
                name="NOTICE", value="Unable to message member about this action.")

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.kick
        await ctx.guild.kick(user=member, reason=reason)

        # Add the kick to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="kick"
            ))

        await ctx.reply(embed=embed)

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(manage_roles=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="mute")
    async def mute(self, ctx: Context, member: discord.Member, *, reason: str):
        """ Mutes member in guild. """

        # TODO: Implement temp/timed mute functionality

        # WARNING: this is worthless if the member leaves and then rejoins. (resets roles)

        # Checks if invoker can action that member (self, bot, etc.)
        if not await self.can_action_member(ctx, member):
            return

        embed = embeds.make_embed(context=ctx, title=f"Muting member: {member.name}",
                                  image_url=config.user_mute, color=config.soft_red)
        embed.description = f"{member.mention} was muted by {ctx.author.mention} for:\n{reason}"

        # Send member message telling them that they were muted and why.
        try:  # Incase user has DM's Blocked.
            channel = await member.create_dm()
            message = f"You were muted in {ctx.guild} for: {reason}"
            await channel.send(message)
        except:
            embed.add_field(
                name="NOTICE", value="Unable to message member about this action.")

        # Adds "Muted" role to member.
        # TODO: Add role name to configuration, maybe by ID?
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if role is None:
            role = await ctx.guild.create_role(name="Muted")
        await member.add_roles(role, reason=reason)

        # Add the mute to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="mute"
            ))

        await ctx.reply(embed=embed)

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(manage_roles=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="unmute")
    async def unmute(self, ctx: Context, member: discord.Member, *, reason: str):
        """ Unmutes member in guild. """

        # Checks if invoker can action that member (self, bot, etc.)
        if not await self.can_action_member(ctx, member):
            return

        embed = embeds.make_embed(context=ctx, title=f"Unmuting member: {member.name}",
                                  image_url=config.user_unmute, color=config.soft_green)
        embed.description = f"{member.mention} was unmuted by {ctx.author.mention} for:\n{reason}"

        # Send member message telling them that they were banned and why.
        try:  # Incase user has DM's Blocked.
            channel = await member.create_dm()
            message = f"You were unmuted in {ctx.guild}. Try to behave in the future!"
            await channel.send(message)
        except:
            embed.add_field(
                name="NOTICE", value="Unable to message member about this action.")

        # Removes "Muted" role from member.
        # TODO: Add role name to configuration, maybe by ID?
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        await member.remove_roles(role, reason=reason)

        # Add the mute to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="unmute"
            ))

        await ctx.reply(embed=embed)

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="warn")
    async def warn(self, ctx: Context, member: discord.Member, *, reason: str):
        """ Sends member a warning DM and logs to database. """

        embed = embeds.make_embed(context=ctx, title=f"Warning member: {member.name}",
                                  image_url=config.user_warn, color=config.soft_orange)
        embed.description = f"{member.mention} was warned by {ctx.author.mention} for:\n{reason}"

        # Send member message telling them that they were warned and why.
        try:  # Incase user has DM's Blocked.
            channel = await member.create_dm()
            message = f"You were warned in {ctx.guild} for: {reason}"
            await channel.send(message)
        except:
            embed.add_field(
                name="NOTICE", value="Unable to message member about this action.")

        # Add the warning to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="warn"
            ))

        # Respond to the context that the member was warned.
        await ctx.reply(embed=embed)

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="addnote", aliases=['add_note', 'note'])
    async def add_note(self, ctx: Context, user: discord.User, *, note: str):
        """ Adds a moderator note to a user. """

        embed = embeds.make_embed(context=ctx, title=f"Noting user: {user.name}",
                                  image_url=config.pencil, color=config.soft_blue)
        embed.description = f"{user.mention} was noted by {ctx.author.mention}:\n{note}"

        # Add the note to the mod_notes database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_notes"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), note=note
            ))

        # Respond to the context that the message was noted.
        await ctx.reply(embed=embed)

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(embed_links=True, manage_messages=True, send_messages=True, read_message_history=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="remove", aliases=['rm', 'purge'])
    async def remove_messages(self, ctx: Context, members: Greedy[discord.Member] = None, number_of_messages: int = 10, *, reason: str):
        """ Scans the number of messages and removes all that match specified members, if none given, remove all. """

        # Checking if the given message falls under the selected members, but if no members given, then remove them all.
        def should_remove(message: discord.Message):
            if members is None:
                return True
            elif message.author in members:
                return True
            return False

        if number_of_messages > 100:
            number_of_messages = 100

        embed = embeds.make_embed(context=ctx, title=f"Removing messages",
                                  image_url=config.message_delete, color=config.soft_red)

        deleted = await ctx.channel.purge(limit=number_of_messages, check=should_remove)

        if members == None:
            embed.description = f"{ctx.author.mention} removed the previous {len(deleted)} messages for:\n{reason}"
        else:
            embed.description = f"""{ctx.author.mention} removed {len(deleted)} message(s) from:\n 
                {', '.join([member.mention for member in members])}\n for:\n{reason}"""
        await ctx.send(embed=embed)

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(embed_links=True, send_messages=True, read_message_history=True)
    @commands.before_invoke(record_usage)
    @commands.group(name="censor", aliases=['automod', 'am'])
    async def censor(self, ctx: Context):
        """ Message auto-moderation feature for Chiya. """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @censor.command(name="list")
    async def censor_list(self, ctx: Context):
        """ Command to list all the currently censored terms. """
        with dataset.connect(utils.database.get_db()) as db:
            query = "SELECT * FROM censor"
            result = db.query(query)
            
            embed = embeds.make_embed(
                "Censored terms list", "List of censored terms", ctx)
            censored_terms_list = ""
            for x in result:
                censored_terms_list += f"{x['censor_term']}\t:\t{x['censor_type']}\n"
            

            if len(censored_terms_list) > 0:
                embed.description = "**Censor Term**\t:\t**Type**\n" + censored_terms_list
                await ctx.send(embed=embed)
                return

            # throws an error if no words are added.
            await embeds.error_message("No terms in censor list!", ctx)

    @censor.command(name="add")
    async def censor_add(self, ctx: Context, censor_type: str, *, censor_term: str):
        """ Command to add censors to the list. """
        censor_types = [
            {
                "name": "substring",
                "aliases": ['substr', 'sub']
            },
            {
                "name": "regex",
                "aliases": ['regex']
            },
            {
                "name": "exact",
                "aliases": ['exact']
            },
            {
                "name": "links",
                "aliases": ['link']
            },
        ]

        # sanitizing input since we're doing exact matches
        censor_type = censor_type.lower()
        censor_type = censor_type.strip()
        censor_term = censor_term.lower()
        censor_term = censor_term.strip()
        for x in censor_types:
            # matching up the
            if (censor_type == x['name'] or censor_type in x['aliases']):
                # adding to the DB and messaging user that action was successful
                with dataset.connect(utils.database.get_db()) as db:
                    db['censor'].insert(dict(
                        censor_term=censor_term,
                        censor_type=x['name']
                    ))
                    await ctx.reply(f"Censor term \"{censor_term}\" of type `{x['name']}` was added.")
                    return

        # User did not specify censor type properly, so throw an error.
        await embeds.error_message("Valid censor types are: `substring`, `regex`, `exact` and `links`.", ctx)

    @censor.command(name="remove", aliases=['delete', 'rm'])
    async def censor_remove(self, ctx: Context, *, term: str):
        """ Command to remove censors from list. """
        with dataset.connect(utils.database.get_db()) as db:
            query = f"SELECT * FROM censor where censor_term ='{term.lower().strip()}'"
            result = db.query(query)
            if(len(list(result)) == 0):
                await embeds.error_message("No such term in censor list!", ctx)
                return

            db['censor'].delete(censor_term = term.lower().strip())
            await ctx.reply(f"Term \"{term.lower().strip()}\" was removed.")

def setup(bot: Bot) -> None:
    """ Load the ModerationCog cog. """
    bot.add_cog(ModerationCog(bot))
    log.info("Cog loaded: ModerationCog")
