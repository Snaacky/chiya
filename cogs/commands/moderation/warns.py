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

class WarnsCog(Cog):
    """ Warns Cog """

    def __init__(self, bot):
        self.bot = bot

    @commands.has_role(config.role_staff)
    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="warn")
    async def warn(self, ctx: Context, member: discord.Member, *, reason: str):
        """ Sends member a warning DM and logs to database. """

        embed = embeds.make_embed(ctx=ctx, title=f"Warning member: {member.name}", 
            image_url=config.user_warn, color="soft_orange")
        embed.description=f"{member.mention} was warned by {ctx.author.mention} for: {reason}"

        if len(reason) > 512:
            await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")
            return

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
            embed.add_field(name="Notice:", value=f"Unable to message {member.mention} about this action. This can be caused by the user not being in the server, having DMs disabled, or having the bot blocked.")

        # Send the warning embed DM to the user.
        await ctx.reply(embed=embed)

        # Add the warning to the mod_log database.
        with dataset.connect(database.get_db()) as db:
            db["mod_logs"].insert(dict(
                user_id=member.id, mod_id=ctx.author.id, timestamp=int(time.time()), reason=reason, type="warn"
            ))

def setup(bot: Bot) -> None:
    """ Load the Notes cog. """
    bot.add_cog(WarnsCog(bot))
    log.info("Commands loaded: warns")
