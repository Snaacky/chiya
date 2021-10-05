import asyncio
import json
import logging

import discord.utils
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

from utils import embeds, database
from utils.config import config
from utils.record import record_usage

log = logging.getLogger(__name__)


class BuyRoleMentionCog(Cog):
    """Buy role mention command cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="buy",
        subcommand_group="role",
        name="mention",
        description="Enables the custom role to be mentionable",
        guild_ids=config["guild_ids"],
        options=[
            create_option(
                name="freeleech",
                description="Enable freeleech for this item, costing 2 freeleech token",
                option_type=5,
                required=False,
            ),
        ],
    )
    async def buy_role_mention(self, ctx: SlashContext, freeleech: bool = False):
        """Enables the custom role to be mentionable"""
        await ctx.defer()

        # Warn if the command is called outside of #bots channel. Using a tuple is more memory efficient.
        if ctx.channel.id not in (
            config["channels"]["bots"],
            config["channels"]["bot_testing"],
        ):
            return await embeds.error_message(ctx=ctx, description="This command can only be run in #bots channel.")

        # Get the LevelingCog for utilities functions.
        leveling_cog = self.bot.get_cog("LevelingCog")

        # Connect to the database and get the economy table.
        db = database.Database().get()
        economy = db["economy"]

        # Attempt to find the user who issued the command.
        user = economy.find_one(user_id=ctx.author.id)

        # If the user is not found, initialize their entry, insert it into the db and get their entry which was previously a NoneType.
        if not user:
            stats_json = await leveling_cog.create_user()
            economy.insert(dict(user_id=ctx.author.id, stats=stats_json))
            user = economy.find_one(user_id=ctx.author.id)

        # Load the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user["stats"])

        # Cost of the transaction. Declared separately to give less headaches on future balance changes.
        cost = 3072
        fl_token = 2

        # Condition: Buffer must be above 3072 MB.
        buffer_check = stats["buffer"] >= cost

        # Condition: Must have at least 1 freeleech token.
        fl_token_check = stats["freeleech_token"] >= fl_token

        # If any of the conditions were not met, return an error embed.
        if not buffer_check or (freeleech and not fl_token_check):
            embed = embeds.make_embed(
                title=f"Transaction failed",
                description="One or more of the following conditions were not met:",
                color="red",
            )
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

            # Dynamically add the reason(s) why the transaction was unsuccessful.
            if not buffer_check:
                embed.add_field(
                    name="​",
                    value=f"**Condition:** You must have at least {await leveling_cog.get_buffer_string(cost)} buffer.",
                    inline=False,
                )
            if freeleech and not fl_token_check:
                embed.add_field(
                    name="​",
                    value="**Condition:** You don't have enough freeleech token.",
                    inline=False,
                )
            db.close()
            return await ctx.send(embed=embed)

        # Send a confirmation embed before proceeding the transaction.
        confirm_embed = embeds.make_embed(color="green")
        if freeleech:
            confirm_embed.description = (
                f"{ctx.author.mention}, enable your custom role to be mentionable for {fl_token} "
                f"freeleech {'tokens' if fl_token > 1 else 'token'}? (yes/no/y/n)"
            )
        else:
            confirm_embed.description = (
                f"{ctx.author.mention}, enable your custom role to be mentionable for {cost} MB? (yes/no/y/n)"
            )
        await ctx.send(embed=confirm_embed)

        # A function to check if the reply is "yes", "no", "y", or "n", and is the command's author in the current channel.
        def check(message):
            return (
                message.author == ctx.author
                and message.channel == ctx.channel
                and message.content.lower() in ("yes", "no", "y", "n")
            )

        # Wait for the user's reply (yes/no/y/n) and return if the response is "no", "n" or no response was received after 60s.
        try:
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            if msg.content.lower() in ("no", "n"):
                embed = embeds.make_embed(
                    description=f"{ctx.author.mention}, your transaction request has been cancelled.",
                    color="red",
                )
                db.close()
                return await ctx.send(embed=embed)
        except asyncio.TimeoutError:
            embed = embeds.make_embed(
                description=f"{ctx.author.mention}, your transaction request has timed out.",
                color="red",
            )
            db.close()
            return await ctx.send(embed=embed)

        role = discord.utils.get(ctx.guild.roles, id=stats["custom_role_id"])

        # A check to make sure that the role actually exists since it's modifiable using the developer console.
        if not role:
            db.close()
            return await embeds.error_message(ctx=ctx, description="This role does not exist.")

        await role.edit(mentionable=True)

        # Create the embed to let the user know that the transaction was a success.
        embed = embeds.make_embed(title=f"Custom role upgraded: {role.name}", color="green")
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        # Update the JSON object accordingly with flexible embed description and field.
        if freeleech:
            stats["freeleech_token"] -= fl_token
            embed.description = (
                f"Successfully purchased role mention for {fl_token} freeleech {'tokens' if fl_token > 1 else 'token'}."
            )
            embed.add_field(
                name="​",
                value=f"**Remaining freeleech tokens:** {stats['freeleech_token']}",
            )
        else:
            stats["buffer"] -= cost
            embed.description = f"Successfully purchased role mention for {cost} MB buffer."
            # Get the formatted buffer string.
            buffer_string = await leveling_cog.get_buffer_string(stats["buffer"])
            embed.add_field(name="​", value=f"**New buffer:** {buffer_string}")

        await ctx.send(embed=embed)

        # Dump the modified JSON into the db and close it.
        stats_json = json.dumps(stats)
        economy.update(dict(id=user["id"], stats=stats_json), ["id"])
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """Load the BuyRoleMention cog."""
    bot.add_cog(BuyRoleMentionCog(bot))
    log.info("Commands loaded: buy_role_mention")
