import logging

import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, Greedy

import config
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)

class PurgeCog(Cog):
    """ Purge Cog """

    def __init__(self, bot):
        self.bot = bot

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(embed_links=True, manage_messages=True, send_messages=True, read_message_history=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="remove", aliases=['rm', 'purge'])
    async def remove_messages(self, ctx: Context, members: Greedy[discord.Member] = None, number_of_messages: int = 10, *, reason: str = None):
        """ Scans the number of messages and removes all that match specified members, if none given, remove all. """

        # Checking if the given message falls under the selected members, but if no members given, then remove them all.
        def should_remove(message: discord.Message):
            if members is None: 
                return True
            elif message.author in members:
                return True
            return False

        # Limit the command at 100 messages maximum to avoid abuse.
        if number_of_messages > 100:
            number_of_messages = 100

        # Add + 1 to compensate for the invoking command message.
        number_of_messages += 1

        # Handle cases where the reason is not provided.
        if not reason:
            reason = "No reason provided."

        if len(reason) > 512:
            await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")
            return

        embed = embeds.make_embed(ctx=ctx, title=f"Removed messages", 
            image_url=config.message_delete, color="soft_red")

        deleted = await ctx.channel.purge(limit=number_of_messages, check=should_remove)

        if members == None:
            embed.description=f"{ctx.author.mention} removed the previous {len(deleted)} messages."
            embed.add_field(name="Reason:", value=reason, inline=False)
        else:
            embed.description=f"""{ctx.author.mention} removed {len(deleted)} message(s) from: {', '.join([member.mention for member in members])} for: {reason}"""
        await ctx.send(embed=embed)

def setup(bot: Bot) -> None:
    """ Load the Purge cog. """
    bot.add_cog(PurgeCog(bot))
    log.info("Commands loaded: purge")
