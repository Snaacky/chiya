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


class UpgradeValueCog(Cog):
    """Upgrade value command cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="upgrade",
        name="brightness",
        description="Allows brighter colors to be rolled",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="amount",
                description="Number of upgrades to purchase",
                option_type=4,
                required=True,
            ),
            create_option(
                name="freeleech",
                description="Enable freeleech for this item, costing 1 freeleech token per level",
                option_type=5,
                required=False,
            ),
        ],
    )
    async def upgrade_value(
        self, ctx: SlashContext, amount: int, freeleech: bool = False
    ):
        """
        Allows brighter colors to be rolled. HSB (brightness) == HSV (value), but we're using the former one
        in wording to make it easier to understand for the end users."""
        await ctx.defer()

        # Warn if the command is called outside of #bots channel. Using a tuple is more memory efficient.
        if ctx.channel.id not in (
            settings.get_value("channel_bots"),
            settings.get_value("channel_bot_testing"),
        ):
            await embeds.error_message(
                ctx=ctx, description="This command can only be run in #bots channel."
            )
            return

        """ 
        If the user enter an arbitrary large "amount" value, the inflated_cost calculation would take forever and create a blocking call
        since the calculation is not asynchronous (see https://discordpy.readthedocs.io/en/stable/faq.html#what-does-blocking-mean),
        effectively freezing up the bot and makes all other tasks fail to execute.
        """
        if amount > 100:
            embed = embeds.make_embed(
                description="The amount of levels to be purchased cannot exceed 100.",
                color="red",
            )
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
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

        # Baseline cost of the transaction. Declared separately to give less headaches on future balance changes.
        cost = 3
        fl_token = 1

        # The actual cost for the purchase is 3 * x (x is from 1-100) - it gets more expensive after every upgrade.
        inflated_cost = 0
        # We +1 in the range because we're calculating the cost starting from the next upgrade.
        for i in range(stats["value_upgrade"] + 1, stats["value_upgrade"] + amount + 1):
            inflated_cost += i * cost

        # Condition: Must have more buffer than the cost of the transaction.
        buffer_check = stats["buffer"] >= inflated_cost

        # Condition: Must have enough freeleech token (base token cost multiplied by amount).
        fl_token_check = stats["freeleech_token"] >= fl_token * amount

        # Condition: Must have purchased at least 1 color pack.
        color_check = len(stats["hue_upgrade"]) > 0

        # Condition: The total number of upgrades must not exceed 100.
        availability_check = amount + stats["value_upgrade"] <= 100

        # Condition: Must already own a custom role.
        custom_role_check = stats["has_custom_role"]

        # If any of the conditions were not met, return an error embed.
        if (
            not buffer_check
            or (freeleech and not fl_token_check)
            or not color_check
            or not availability_check
            or not custom_role_check
        ):
            embed = embeds.make_embed(
                title="Transaction failed",
                description="One or more of the following conditions were not met:",
                color="red",
            )
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

            # Dynamically add the reason(s) why the transaction was unsuccessful.
            if not buffer_check and availability_check:
                embed.add_field(
                    name="​",
                    value=f"**Condition:** You must have at least {await leveling_cog.get_buffer_string(inflated_cost)} buffer.",
                    inline=False,
                )
            if not color_check:
                embed.add_field(
                    name="​",
                    value="**Condition:** You must have purchased at least one color pack.",
                    inline=False,
                )
            if not custom_role_check:
                embed.add_field(
                    name="​",
                    value="**Condition:** You must own a custom role.",
                    inline=False,
                )
            if not availability_check:
                embed.add_field(
                    name="​",
                    value=f"**Condition:** You can only purchase this upgrade {100 - stats['value_upgrade']} more times!",
                    inline=False,
                )
            if freeleech and not fl_token_check:
                embed.add_field(
                    name="​",
                    value="**Condition:** You don't have enough freeleech token.",
                    inline=False,
                )
            await ctx.send(embed=embed)
            db.close()
            return

        # Send a confirmation embed before proceeding the transaction.
        confirm_embed = embeds.make_embed(color="green")
        if freeleech:
            confirm_embed.description = (
                f"{ctx.author.mention}, reach the level {stats['value_upgrade'] + amount} of brightness upgrade "
                f"for {fl_token * amount} freeleech {'tokens' if amount > 1 else 'token'}? (yes/no/y/n)"
            )
        else:
            confirm_embed.description = (
                f"{ctx.author.mention}, reach the level {stats['value_upgrade'] + amount} of brightness upgrade "
                f"for {inflated_cost} MB? (yes/no/y/n)"
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
                await ctx.send(embed=embed)
                db.close()
                return
        except asyncio.TimeoutError:
            embed = embeds.make_embed(
                description=f"{ctx.author.mention}, your transaction request has timed out.",
                color="red",
            )
            await ctx.send(embed=embed)
            db.close()
            return

        # Update the new stat first so that the embed will contain the up to date value.
        stats["value_upgrade"] += amount

        # Create an embed upon successful transaction.
        embed = embeds.make_embed(
            title=f"Upgrade purchased: brightness",
            description=f"You reached brightness level {stats['value_upgrade']}!",
            color="green",
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        # Update the JSON object accordingly with flexible embed description and field.
        if freeleech:
            stats["freeleech_token"] -= fl_token * amount
            embed.description = (
                f"Successfully reached brightness level {stats['brightness_upgrade']} for {fl_token * amount} "
                f"freeleech {'tokens' if fl_token > 1 else 'token'}."
            )
            embed.add_field(
                name="​",
                value=f"**Remaining freeleech tokens:** {stats['freeleech_token']}",
            )
        else:
            stats["buffer"] -= inflated_cost
            embed.description = f"Successfully reached brightness level {stats['value_upgrade']} for {inflated_cost} MB."
            # Get the formatted buffer string.
            buffer_string = await leveling_cog.get_buffer_string(stats["buffer"])
            embed.add_field(name="​", value=f"**New buffer:** {buffer_string}")

        await ctx.send(embed=embed)

        # Dump the modified JSON into the db and close it.
        stats_json = json.dumps(stats)
        achievements.update(dict(id=user["id"], stats=stats_json), ["id"])
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """Load the UpgradeValue cog."""
    bot.add_cog(UpgradeValueCog(bot))
    log.info("Commands loaded: upgrade_value")
