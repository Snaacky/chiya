import asyncio
import datetime
import logging
import time

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, Greedy

import config
from utils import database
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
            await ctx.reply("I cannot action that member because their role is higher than mine.")
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
        
        # Checks to see if the user is already banned.
        try:
            await ctx.guild.fetch_ban(user)
            await ctx.reply("That user is already banned.")
            return
        except discord.NotFound:
            pass
    
        embed = embeds.make_embed(context=ctx, title=f"Banning user: {user.name}", 
            image_url=config.user_ban, color=config.soft_red)
        embed.description=f"{user.mention} was banned by {ctx.author.mention} for:\n{reason}"

        # Send user message telling them that they were banned and why.
        try: # Incase user has DM's Blocked.
            channel = await user.create_dm()
            ban_embed = embeds.make_embed(author=False, color=0xc2bac0)
            ban_embed.title = f"Uh-oh, you've been banned!"
            ban_embed.description = "You can submit a ban appeal on our subreddit [here](https://www.reddit.com/message/compose/?to=/r/animepiracy)."
            ban_embed.add_field(name="Server:", value=ctx.guild, inline=True)
            ban_embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            ban_embed.add_field(name="Length:", value="Indefinite", inline=True)
            ban_embed.add_field(name="Reason:", value=reason, inline=False)
            ban_embed.set_image(url="https://i.imgur.com/CglQwK5.gif")
            await channel.send(embed=ban_embed)
        except:
            embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. User either has DMs disabled or the bot blocked.")

        # Send the ban DM to the user.
        await ctx.reply(embed=embed)

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.ban
        await ctx.guild.ban(user=user, reason=reason, delete_message_days=0)

        # Add the ban to the mod_log database.
        with dataset.connect(database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="ban"
            ))

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(ban_members=True, send_messages=True, embed_links=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="unban")
    async def unban_member(self, ctx: Context, user: discord.User, *, reason: str):
        """ Unbans user from guild. """
        
        # Checks to see if the user is actually banned.
        try:
            await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            await ctx.reply("That user is not banned.")
            return

        embed = embeds.make_embed(context=ctx, title=f"Unbanning user: {user.name}", 
            image_url=config.user_unban, color=config.soft_green)
        embed.description=f"{user.mention} was unbanned by {ctx.author.mention} for:\n{reason}"
        await ctx.reply(embed=embed)

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.unban
        await ctx.guild.unban(user=user, reason=reason)

        # Add the unban to the mod_log database.
        with dataset.connect(database.get_db()) as db:
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

        # Send user message telling them that they were kicked and why.
        try: # Incase user has DM's Blocked.
            channel = await member.create_dm()
            kick_embed = embeds.make_embed(author=False, color=0xe49bb3)
            kick_embed.title = f"Uh-oh, you've been kicked!"
            kick_embed.description = "I-I guess you can join back if you want? B-baka. https://discord.gg/piracy"
            kick_embed.add_field(name="Server:", value=ctx.guild, inline=True)
            kick_embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            kick_embed.add_field(name="Reason:", value=reason, inline=False)
            kick_embed.set_image(url="https://i.imgur.com/UkrBRur.gif")
            await channel.send(embed=kick_embed)
        except:
            embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. User either has DMs disabled or the bot blocked.")

        # Send the kick DM to the user.
        await ctx.reply(embed=embed)

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.kick
        await ctx.guild.kick(user=member, reason=reason)

        # Add the kick to the mod_log database.
        with dataset.connect(database.get_db()) as db:
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

        # Check if the user is muted already.
        if discord.utils.get(ctx.guild.roles, id=config.role_muted) in member.roles:
            await ctx.reply("That user is already muted.")
            return

        embed = embeds.make_embed(context=ctx, title=f"Muting member: {member.name}",
            image_url=config.user_mute, color=config.soft_red)
        embed.description=f"{member.mention} was muted by {ctx.author.mention} for:\n{reason}"

        # Creates a channel for users to appeal/discuss their mute
        guild = ctx.message.guild
        category = discord.utils.get(guild.categories, id=config.ticket_category_id)

        # Create a channel in the tickets category specified in the config.     
        mute_channel = await guild.create_text_channel(f"mute-{member.id}", category=category)

        # Give both the staff and the user perms to access the channel. 
        await mute_channel.set_permissions(discord.utils.get(guild.roles, id=config.role_trial_mod), read_messages=True)
        await mute_channel.set_permissions(discord.utils.get(guild.roles, id=config.role_staff), read_messages=True)
        await mute_channel.set_permissions(member, read_messages=True)

        mute_channel_embed = embeds.make_embed(title="🤐 You were muted", description="If you have any questions or concerns about your mute, you may voice them here.")
        mute_channel_embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
        mute_channel_embed.add_field(name="Length:", value="Indefinite.", inline=True) # TODO: Implement timed mutes
        mute_channel_embed.add_field(name="Reason:", value=reason, inline=False)
        

        await mute_channel.send(embed=mute_channel_embed)

        # Send member message telling them that they were muted and why.
        try: # Incase user has DM's Blocked.
            channel = await member.create_dm()
            mute_embed = embeds.make_embed(author=False, color=0x8083b0)
            mute_embed.title = f"Uh-oh, you've been muted!"
            mute_embed.description = "If you believe this was a mistake, contact staff."
            mute_embed.add_field(name="Server:", value=ctx.guild, inline=True)
            mute_embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            mute_embed.add_field(name="Length:", value="Indefinite", inline=True) # TODO: Implement timed mutes.
            mute_embed.add_field(name="Mute Channel:", value=mute_channel.mention, inline=True)
            mute_embed.add_field(name="Reason:", value=reason, inline=False)
            mute_embed.set_image(url="https://i.imgur.com/KE1jNl3.gif")
            await channel.send(embed=mute_embed)
        except:
            embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. User either has DMs disabled or the bot blocked.")

        # Send the mute embed DM to the user.
        await ctx.reply(embed=embed)

        # Adds "Muted" role to member.
        role = discord.utils.get(ctx.guild.roles, id=config.role_muted)
        await member.add_roles(role, reason=reason)

        # Add the mute to the mod_log database.
        with dataset.connect(database.get_db()) as db:
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

        # Check if the user is actually muted.
        if discord.utils.get(ctx.guild.roles, id=config.role_muted) not in member.roles:
            await ctx.reply("That user is not muted.")
            return

        embed = embeds.make_embed(context=ctx, title=f"Unmuting member: {member.name}",
            image_url=config.user_unmute, color=config.soft_green)
        embed.description=f"{member.mention} was unmuted by {ctx.author.mention} for:\n{reason}"
        
        # Send member message telling them that they were banned and why.
        try: # Incase user has DM's Blocked.
            channel = await member.create_dm()
            unmute_embed = embeds.make_embed(author=False, color=0x8a3ac5)
            unmute_embed.title = f"Yay, you've been unmuted!"
            unmute_embed.description = "Review our server rules to avoid being actioned again in the future."
            unmute_embed.add_field(name="Server:", value=ctx.guild, inline=True)
            unmute_embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            unmute_embed.add_field(name="Reason:", value=reason, inline=False)
            unmute_embed.set_image(url="https://i.imgur.com/U5Fvr2Y.gif")
            await channel.send(embed=unmute_embed)
        except:
            embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. User either has DMs disabled or the bot blocked.")

        # Send the unmute embed DM to the user.
        await ctx.reply(embed=embed)

        # Removes "Muted" role from member.
        # TODO: Add role name to configuration, maybe by ID?
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        await member.remove_roles(role, reason=reason)

        # archives mute channel
        mute_category = discord.utils.get(ctx.guild.categories, id=config.ticket_category_id)
        channel = discord.utils.get(mute_category.channels, name=f"mute-{member.id}")
        
        archive = discord.utils.get(ctx.guild.categories, id=config.archive_category)
        await channel.edit(category=archive, sync_permissions=True)

        # Add the mute to the mod_log database.
        with dataset.connect(database.get_db()) as db:
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
        
        # Send member message telling them that they were warned and why.
        try: # Incase user has DM's Blocked.
            channel = await member.create_dm()
            warn_embed = embeds.make_embed(author=False, color=0xf7dcad)
            warn_embed.title = f"Uh-oh, you've received a warning!"
            warn_embed.description = "If you believe this was a mistake, contact staff."
            warn_embed.add_field(name="Server:", value=ctx.guild, inline=True)
            warn_embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            warn_embed.add_field(name="Reason:", value=reason, inline=False)
            warn_embed.set_image(url="https://i.imgur.com/rVf0mlG.gif")
            await channel.send(embed=warn_embed)
        except:
            embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. User either has DMs disabled or the bot blocked.")

        # Send the warning embed DM to the user.
        await ctx.reply(embed=embed)

        # Add the warning to the mod_log database.
        with dataset.connect(database.get_db()) as db:
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
        with dataset.connect(database.get_db()) as db:
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


    @commands.has_role(config.role_staff)
    @commands.before_invoke(record_usage)
    @commands.group()
    async def ticket(self, ctx):
        if ctx.invoked_subcommand is None:
            # Send the help command for this group
            await ctx.send_help(ctx.command)


    @commands.has_role(config.role_staff)
    @commands.before_invoke(record_usage)
    @ticket.command(name="close")
    async def close(self, ctx):
        """ Closes the modmail ticket."""
        channel = ctx.message.channel

        if not channel.category_id == config.ticket_category_id:
            embed = embeds.make_embed(color=config.soft_red)
            embed.description=f"You can only run this command in active ticket channels."
            await ctx.reply(embed=embed)
            return

        # Send notice that the channel has been marked read only and will be archived.
        embed = embeds.make_embed(author=False, color=0xffffc3)
        embed.title = f"🔒 Your ticket has been closed."
        embed.description = f"The channel has been marked read-only and will be archived in one minute. If you have additional comments or concerns, feel free to open another ticket."
        embed.set_image(url="https://i.imgur.com/TodlFQq.gif")
        await ctx.send(embed=embed)

        # Set the channel into a read only state.
        for role in channel.overwrites:
            # default_role is @everyone role, so skip that.
            if role == ctx.guild.default_role:
                continue

            await channel.set_permissions(role, read_messages=True, send_messages=False, add_reactions=False, 
                                                manage_messages=False)     

        with dataset.connect(database.get_db()) as db:
            table = db["tickets"]
            ticket = table.find_one(user_id=int(ctx.channel.name.replace("ticket-", "")), status=1)
            ticket["status"] = 2
            table.update(ticket, ["id"])           

        # Sleep for 60 seconds before archiving the channel.
        await asyncio.sleep(60)

        # Move the channel to the archive.
        archive = discord.utils.get(ctx.guild.categories, id=config.archive_category)
        await ctx.channel.edit(category=archive, sync_permissions=True)
        

def setup(bot: Bot) -> None:
    """ Load the ModerationCog cog. """
    bot.add_cog(ModerationCog(bot))
    log.info("Commands loaded: moderation")
