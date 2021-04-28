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

class NotesCog(Cog):
    """ Notes Cog """

    def __init__(self, bot):
        self.bot = bot

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="addnote", aliases=['add_note', 'note'])
    async def add_note(self, ctx: Context, user: discord.User, *, note: str):
        """ Adds a moderator note to a user. """

        embed = embeds.make_embed(ctx=ctx, title=f"Noting user: {user.name}", 
            image_url=config.pencil, color=config.soft_blue)
        embed.description=f"{user.mention} was noted by {ctx.author.mention}: {note}"
        await ctx.reply(embed=embed)

        # Add the note to the mod_notes database.
        with dataset.connect(database.get_db()) as db:
            db["mod_notes"].insert(dict(
                user_id=user.id, mod_id=ctx.author.id, timestamp=int(time.time()), note=note
            ))

def setup(bot: Bot) -> None:
    """ Load the Notes cog. """
    bot.add_cog(NotesCog(bot))
    log.info("Commands loaded: notes")
