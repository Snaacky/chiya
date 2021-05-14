import datetime
import logging
import re
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

class BanCog(Cog):
    """ Ban Cog """

    def __init__(self, bot):
        self.bot = bot

    async def can_action_member(self, ctx: Context, member: discord.Member) -> bool:
        """ Stop mods from doing stupid things. """
        # Stop mods from actioning on the bot.
        if member.id == self.bot.user.id:
            await embeds.error_message(ctx=ctx, description="You cannot action that member due to hierarchy.")
            return False

        # Stop mods from actioning one another, people higher ranked than them or themselves.
        if member.top_role >= ctx.author.top_role:
            await embeds.error_message(ctx=ctx, description="You cannot action that member due to hierarchy.")
            return False

        # Checking if Bot is able to even perform the action
        if member.top_role >= member.guild.me.top_role:
            await embeds.error_message(ctx=ctx, description="I cannot action that member.")
            return False

        # Otherwise, the action is probably valid, return true.
        return True

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(ban_members=True, send_messages=True, embed_links=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="ban")
    async def ban_member(self, ctx: Context, user: discord.User, *, reason: str = None):
        """ Bans user from guild. """

        # Checking if user is in guild.
        member = ctx.guild.get_member(user.id)
        if member:
            # Checks if invoker can action that member (self, bot, etc.)
            if not await self.can_action_member(ctx=ctx, member=member):
                return
        
        # Checks to see if the user is already banned.
        try:
            await ctx.guild.fetch_ban(user)
            await embeds.error_message(ctx=ctx, description=f"{user.mention} is already banned.")
            return
        except discord.NotFound:
            pass

        # Handle cases where the reason is not provided.
        if not reason:
            reason = "No reason provided."
            
        if len(reason) > 512:
            await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")
            return
    
        embed = embeds.make_embed(ctx=ctx, title=f"Banning user: {user.name}", 
            image_url=config.user_ban, color="soft_red")
        embed.description=f"{user.mention} was banned by {ctx.author.mention} for: {reason}"

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
            embed.add_field(name="Notice:", value=f"Unable to message {user.mention} about this action. This can be caused by the user not being in the server, having DMs disabled, or having the bot blocked.")

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
    async def unban_member(self, ctx: Context, user: discord.User, *, reason: str = None):
        """ Unbans user from guild. """
        
        # Checks to see if the user is actually banned.
        try:
            await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            await embeds.error_message(ctx=ctx, description=f"{user.mention} is not banned.")
            return

        # Handle cases where the reason is not provided.
        if not reason:
            reason = "No reason provided."
            
        if len(reason) > 512:
            await embeds.error_message(ctx=ctx, description=f"Reason must be less than 512 characters.")
            return

        embed = embeds.make_embed(ctx=ctx, title=f"Unbanning user: {user.name}", 
            image_url=config.user_unban, color="soft_green")
        embed.description=f"{user.mention} was unbanned by {ctx.author.mention} for: {reason}"
        await ctx.reply(embed=embed)

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.unban
        await ctx.guild.unban(user=user, reason=reason)

        # Add the unban to the mod_log database.
        with dataset.connect(database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="unban"
            ))
    
    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(ban_members=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="tempban")
    async def temp_ban(self, ctx: Context, user: discord.User, *, reason_and_duration: str):
        """ Temporarily bans member from guild. """

        # regex stolen from setsudo
        regex = r"((?:(\d+)\s*d(?:ays)?)?\s*(?:(\d+)\s*h(?:ours|rs|r)?)?\s*(?:(\d+)\s*m(?:inutes|in)?)?\s*(?:(\d+)\s*s(?:econds|ec)?)?)(?:\s+([\w\W]+))"

        # Checking if user is in guild.
        if ctx.guild.get_member(user.id):
            # Convert to member object
            member = await commands.MemberConverter().convert(ctx, user.mention)

            # Checks if invoker can action that member (self, bot, etc.)
            if not await self.can_action_member(ctx, member):
                return
        
        # Checks to see if the user is already banned.
        try:
            await ctx.guild.fetch_ban(user)
            await embeds.error_message(ctx=ctx, description=f"{user.mention} is already banned.")
            return
        except discord.NotFound:
            pass

        embed = embeds.make_embed(ctx=ctx, title=f"Banning user: {user}", 
            image_url=config.user_ban, color="soft_red")
        
        # getting the matches from the regex
        try:
            match_list = re.findall(regex, reason_and_duration)[0]
        except:
            await embeds.error_message(ctx, "Syntax: `tempban <x>d<y>h<z>m<a>s <reason>`")
            return

        reason = match_list[5]
        
        duration = dict(
            days = match_list[1],
            hours = match_list[2],
            minutes = match_list[3],
            seconds = match_list[4]
        )
        
        # string that'll store the duration to be displayed later.
        duration_string = ''
        
        for time_unit in duration:
            if len(duration[time_unit]):
                duration_string += f"{duration[time_unit]} {time_unit} "
                # updating the values for ease of conversion to timedelta object later.
                duration[time_unit] = float(duration[time_unit])
            else:
                # value defaults to 0 in case nothing was mentioned
                duration[time_unit] = 0

        ban_start_time = datetime.datetime.now(tz=datetime.timezone.utc)
        ban_end_time = ban_start_time + datetime.timedelta(
            days = duration['days'],
            hours = duration['hours'],
            minutes = duration['minutes'],
            seconds = duration['seconds']
        ) 

        # Send member message telling them that they were muted and why.
        try: # Incase user has DM's Blocked.
            channel = await user.create_dm()
            ban_embed = embeds.make_embed(author=False, color=0xc2bac0)
            ban_embed.title = f"Uh-oh, you've been banned!"
            ban_embed.description = "You can submit a ban appeal on our subreddit [here](https://www.reddit.com/message/compose/?to=/r/animepiracy)."
            ban_embed.add_field(name="Server:", value=ctx.guild, inline=True)
            ban_embed.add_field(name="Moderator:", value=ctx.message.author.mention, inline=True)
            ban_embed.add_field(name="Length:", value=duration_string, inline=True)
            ban_embed.add_field(name="Reason:", value=reason, inline=False)
            ban_embed.set_image(url="https://i.imgur.com/CglQwK5.gif")
            await channel.send(embed=ban_embed)
        except:
            embed.add_field(name="Notice:", value=f"Unable to message {user.mention} about this action. This can be caused by the user not being in the server, having DMs disabled, or having the bot blocked.")

        # Info: https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.ban
        await ctx.guild.ban(user=user, reason=reason, delete_message_days=0)
        
        # Add the mute to the database(s)
        with dataset.connect(database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=ban_start_time.timestamp(), reason=reason, type="ban"
            ))
            db["timed_mod_actions"].insert(dict(
                user_id = user.id,
                mod_id = ctx.author.id,
                channel_id = ctx.message.channel.id,
                action_type = 'ban',
                reason = reason,
                start_time = ban_start_time.timestamp(),
                end_time = ban_end_time.timestamp(),
                is_done = False
            ))
        
        embed.description=f"{user.mention} was banned by {ctx.author.mention} for:\n{reason}\n **Duration:** {duration_string}"
        await ctx.reply(embed=embed)

def setup(bot: Bot) -> None:
    """ Load the Ban cog. """
    bot.add_cog(BanCog(bot))
    log.info("Commands loaded: bans")
