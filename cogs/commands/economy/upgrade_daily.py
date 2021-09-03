import asyncio
import json
import logging

import dataset
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

from cogs.commands import settings
from utils import embeds, database
from utils.record import record_usage

log = logging.getLogger(__name__)


class UpgradeDailyCog(Cog):
    """ Upgrade daily command cog. """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="upgrade",
        name="daily",
        description="Increases the chance to receive 2x buffer from /daily",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="amount",
                description="Number of upgrades to purchase.",
                option_type=4,
                required=True
            ),
            create_option(
                name="freeleech",
                description="Enable freeleech for this item, costing 1 freeleech token per level.",
                option_type=5,
                required=False
            ),
        ],
    )
    async def upgrade_daily(self, ctx: SlashContext, amount: int, freeleech: bool = False):
        """ Increases the chance to receive 2x buffer from /daily. """
        await ctx.defer()

        # Warn if the command is called outside of #bots channel.
        if not ctx.channel.id == settings.get_value("channel_bots") and not ctx.channel.id == settings.get_value("channel_bot_testing"):
            await embeds.error_message(ctx=ctx, description="You can only run this command in #bots channel.")
            return

        # Get the LevelingCog for utilities functions.
        leveling_cog = self.bot.get_cog("LevelingCog")

        # Connect to the database and get the achievement table.
        db = dataset.connect(database.get_db())
        achievements = db["achievements"]

        # Attempt to find the user who issued the command.
        user = achievements.find_one(user_id=ctx.author.id)

        # If the user is not found, initialize their entry, insert it into the db and get their entry which was previously a NoneType.
        if not user:
            stats_json = await leveling_cog.create_user()
            achievements.insert(dict(user_id=ctx.author.id, stats=stats_json))
            user = achievements.find_one(user_id=ctx.author.id)

        # Loads the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user["stats"])

        # Check the integrity of the stats dictionary and add any potential missing keys.
        stats = await leveling_cog.verify_integrity(stats)

        # Baseline cost of the transaction. Declared separately to give less headaches on future balance changes.
        cost = 5
        fl_token = 1

        # The actual cost for the purchase is 3 * x (x is from 1-100) - it gets more expensive after every upgrade.
        inflated_cost = 0
        # We +1 in the range because we're calculating the cost starting from the next upgrade.
        for i in range(stats["daily_upgrade"] + 1, stats["daily_upgrade"] + amount + 1):
            inflated_cost += i * cost

        # Condition: Must have more buffer than the cost of the transaction.
        buffer_check = stats["buffer"] >= inflated_cost

        # Condition: Must have at least 1 freeleech token.
        fl_token_check = stats["freeleech_token"] >= fl_token

        # Condition: The total number of upgrades must not exceed 100.
        availability_check = amount + stats["daily_upgrade"] <= 100

        # If any of the conditions were not met, return an error embed.
        if not buffer_check or not fl_token_check or not availability_check:
            embed = embeds.make_embed(
                title="Transaction failed",
                description="One or more of the following conditions were not met:",
                color="red"
            )
            # Dynamically add the reason(s) why the transaction was unsuccessful.
            # Only display this message when the total number of upgrades are below 100.
            if not buffer_check and availability_check:
                embed.add_field(name="Condition:", value=f"You must have at least {await leveling_cog.get_buffer_string(inflated_cost)} buffer.", inline=False)
            if not availability_check:
                embed.add_field(name="Condition:", value=f" You can only purchase this upgrade {100 - stats['daily_upgrade']} more times!", inline=False)
            if freeleech and not fl_token_check:
                embed.add_field(name="Condition:", value="You don't have enough freeleech token.", inline=False)
            await ctx.send(embed=embed)
            db.close()
            return

        # Send a confirmation embed before proceeding the transaction.
        confirm_embed = embeds.make_embed(color="green")
        if freeleech:
            confirm_embed.description = f"{ctx.author.mention}, reach the level {stats['daily_upgrade'] + amount} of " \
                                        f"daily upgrade for {fl_token * amount} freeleech token? (y/n)"
        else:
            confirm_embed.description = f"{ctx.author.mention}, reach the level {stats['daily_upgrade'] + amount} of " \
                                        f"daily upgrade for {inflated_cost} MB? (y/n)"
        await ctx.send(embed=confirm_embed)

        # A function to check if the reply is yes/y/no/n and is the command's author in the current channel.
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() in ["yes", "y", "no", "n"]

        # Wait for the user's reply (yes/y/no/n) and return if the response is "no" or "n" or no response was received after 60s.
        try:
            msg = await self.bot.wait_for("message", timeout=60, check=check)
            if msg.content.lower() == "no" or msg.content.lower() == "n":
                embed = embeds.make_embed(description=f"{ctx.author.mention}, your transaction request has been cancelled.", color="red")
                await ctx.send(embed=embed)
                db.close()
                return
        except asyncio.TimeoutError:
            embed = embeds.make_embed(description=f"{ctx.author.mention}, your transaction request has timed out.", color="red")
            await ctx.send(embed=embed)
            db.close()
            return

        # Update the new stat first so that the embed will contain the up to date value.
        stats["daily_upgrade"] += amount

        # Create an embed upon successful transaction and notice the user if the buffer was doubled.
        embed = embeds.make_embed(
            title=f"Upgrade purchased: daily",
            description=f"You reached daily level {stats['daily_upgrade']}!",
            color="green"
        )
        embed.add_field(name="​", value=f"**Chance to receive 2x buffer:** {round(stats['daily_upgrade'] * 0.35, 2)}%", inline=False)

        # Update the JSON object accordingly.
        if freeleech:
            stats["freeleech_token"] -= fl_token * amount
            embed.add_field(name="​", value=f"**Remaining freeleech tokens:** {stats['freeleech_token']}")
        else:
            stats["buffer"] -= inflated_cost
            # Get the formatted buffer string.
            buffer_string = await leveling_cog.get_buffer_string(stats["buffer"])
            embed.add_field(name="​", value=f"**New buffer:** {buffer_string}")

        await ctx.send(embed=embed)

        # Dump the modified JSON into the db and close it.
        stats_json = json.dumps(stats)
        achievements.update(dict(id=user["id"], stats=stats_json), ["id"])

        # Commit the changes to the database and close it.
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """ Load the UpgradeDaily cog. """
    bot.add_cog(UpgradeDailyCog(bot))
    log.info("Commands loaded: upgrade_daily")
