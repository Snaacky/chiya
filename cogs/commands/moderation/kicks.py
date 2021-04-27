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

class KickCog(Cog):
    """ Kick Cog """

    def __init__(self, bot):
        self.bot = bot

    async def can_action_member(self, ctx: Context, member: discord.Member) -> bool:
        """ Stop mods from doing stupid things. """
        # Stop mods from actioning on the bot.
        if member.id == self.bot.user.id:
            embed = embeds.make_embed(color=config.soft_red)
            embed.description=f"You cannot action that member."
            await ctx.reply(embed=embed)
            return False

        # Stop mods from actioning one another, people higher ranked than them or themselves.
        if member.top_role >= ctx.author.top_role:
            embed = embeds.make_embed(color=config.soft_red)
            embed.description=f"You cannot action that member."
            await ctx.reply(embed=embed)
            return False

        # Checking if Bot is able to even perform the action
        if member.top_role >= member.guild.me.top_role:
            embed = embeds.make_embed(color=config.soft_red)
            embed.description=f"I cannot action that member."
            await ctx.reply(embed=embed)
            return False

        # Otherwise, the action is probably valid, return true.
        return True

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

def setup(bot: Bot) -> None:
    """ Load the Kick cog. """
    bot.add_cog(KickCog(bot))
    log.info("Commands loaded: kicks")
