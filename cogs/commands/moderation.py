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
            await ctx.reply("I cannot action that member because I have an equal or lower role than them.")
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
        embed.description=f"{user.mention} was banned by {ctx.author.mention} for:\n{reason}"
        await ctx.reply(embed=embed)

        # Send user message telling them that they were banned and why.
        try: # Incase user has DM's Blocked.
            channel = await user.create_dm()
            embed = embeds.make_embed(author=False, color=0xc2bac0)
            embed.title = f"Uh-oh, you've been banned!"
            embed.description = "You can submit a ban appeal on our subreddit [here](https://www.reddit.com/message/compose/?to=/r/animepiracy)."
            embed.add_field(name="Server:", value=ctx.guild, inline=True)
            embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            embed.add_field(name="Length:", value="Indefinite", inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/CglQwK5.gif")
            await channel.send(embed=embed)
        except:
            embed.add_field(name="NOTICE", value="Unable to message user about this action.")

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.ban
        await ctx.guild.ban(user=user, reason=reason, delete_message_days=0)

        # Add the ban to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="ban"
            ))

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(ban_members=True, send_messages=True, embed_links=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="unban")
    async def unban_member(self, ctx: Context, user: discord.User, *, reason: str):
        """ Unbans user from guild. """

        embed = embeds.make_embed(context=ctx, title=f"Unbanning user: {user.name}", 
            image_url=config.user_unban, color=config.soft_green)
        embed.description=f"{user.mention} was unbanned by {ctx.author.mention} for:\n{reason}"
        await ctx.reply(embed=embed)

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.unban
        await ctx.guild.unban(user=user, reason=reason)

        # Add the unban to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="unban"
            ))

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
        embed.description=f"{member.mention} was kicked by {ctx.author.mention} for:\n{reason}"
        await ctx.reply(embed=embed)

        # Send user message telling them that they were kicked and why.
        try: # Incase user has DM's Blocked.
            channel = await member.create_dm()
            embed = embeds.make_embed(author=False, color=0xe49bb3)
            embed.title = f"Uh-oh, you've been kicked!"
            embed.description = "I-I guess you can join back if you want? B-baka. https://discord.gg/piracy"
            embed.add_field(name="Server:", value=ctx.guild, inline=True)
            embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/UkrBRur.gif")
            await channel.send(embed=embed)
        except:
            embed.add_field(name="NOTICE", value="Unable to message member about this action.")

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.kick
        await ctx.guild.kick(user=member, reason=reason)

        # Add the kick to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="kick"
            ))

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(manage_roles=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="mute")
    async def mute(self, ctx: Context, member: discord.Member, *, reason: str):
        """ Mutes member in guild. """
        # TODO: Implement temp/timed mute functionality
        # NOTE: this is worthless if the member leaves and then rejoins. (resets roles)

        # Checks if invoker can action that member (self, bot, etc.)
        if not await self.can_action_member(ctx, member):
            return

        embed = embeds.make_embed(context=ctx, title=f"Muting member: {member.name}",
            image_url=config.user_mute, color=config.soft_red)
        embed.description=f"{member.mention} was muted by {ctx.author.mention} for:\n{reason}"
        await ctx.reply(embed=embed)

        # Send member message telling them that they were muted and why.
        try: # Incase user has DM's Blocked.
            channel = await member.create_dm()
            embed = embeds.make_embed(author=False, color=0x8083b0)
            embed.title = f"Uh-oh, you've been muted!"
            embed.description = "Review our server rules to avoid being actioned again in the future. If you believe this was a mistake, contact staff."
            embed.add_field(name="Server:", value=ctx.guild, inline=True)
            embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            embed.add_field(name="Length:", value="Indefinite", inline=True) # TODO: Implement timed mutes.
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/KE1jNl3.gif")
            await channel.send(embed=embed)
        except:
            embed.add_field(name="NOTICE", value="Unable to message member about this action.")

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
        embed.description=f"{member.mention} was unmuted by {ctx.author.mention} for:\n{reason}"
        await ctx.reply(embed=embed)
        
        # Send member message telling them that they were banned and why.
        try: # Incase user has DM's Blocked.
            channel = await member.create_dm()
            embed = embeds.make_embed(author=False, color=0x8a3ac5)
            embed.title = f"Yay, you've been unmuted!"
            embed.description = "Review our server rules to avoid being actioned again in the future."
            embed.add_field(name="Server:", value=ctx.guild, inline=True)
            embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/U5Fvr2Y.gif")
            await channel.send(embed=embed)
        except:
            embed.add_field(name="NOTICE", value="Unable to message member about this action.")

        # Removes "Muted" role from member.
        # TODO: Add role name to configuration, maybe by ID?
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        await member.remove_roles(role, reason=reason)

        # Add the mute to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="unmute"
            ))

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="warn")
    async def warn(self, ctx: Context, member: discord.Member, *, reason: str):
        """ Sends member a warning DM and logs to database. """

        embed = embeds.make_embed(context=ctx, title=f"Warning member: {member.name}", 
            image_url=config.user_warn, color=config.soft_orange)
        embed.description=f"{member.mention} was warned by {ctx.author.mention} for:\n{reason}"
        await ctx.reply(embed=embed)

        # Send member message telling them that they were warned and why.
        try: # Incase user has DM's Blocked.
            channel = await member.create_dm()
            embed = embeds.make_embed(author=False, color=0xf7dcad)
            embed.title = f"Uh-oh, you've received a warning!"
            embed.description = "If you believe this was a mistake, contact staff."
            embed.add_field(name="Server:", value=ctx.guild, inline=True)
            embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/rVf0mlG.gif")
            await channel.send(embed=embed)
        except:
            embed.add_field(name="NOTICE", value="Unable to message member about this action.")

        # Add the warning to the mod_log database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="warn"
            ))

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="addnote", aliases=['add_note', 'note'])
    async def add_note(self, ctx: Context, user: discord.User, *, note: str):
        """ Adds a moderator note to a user. """

        embed = embeds.make_embed(context=ctx, title=f"Noting user: {user.name}", 
            image_url=config.pencil, color=config.soft_blue)
        embed.description=f"{user.mention} was noted by {ctx.author.mention}:\n{note}"
        await ctx.reply(embed=embed)

        # Add the note to the mod_notes database.
        with dataset.connect(utils.database.get_db()) as db:
            db["mod_notes"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), note=note
            ))


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
            embed.description=f"{ctx.author.mention} removed the previous {len(deleted)} messages for:\n{reason}"
        else:
            embed.description=f"""{ctx.author.mention} removed {len(deleted)} message(s) from:\n 
                {', '.join([member.mention for member in members])}\n for:\n{reason}"""
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    """ Load the ModerationCog cog. """
    bot.add_cog(ModerationCog(bot))
    log.info("Cog loaded: ModerationCog")
