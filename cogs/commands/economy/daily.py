import json
import logging
import random
import time

from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext

from utils import embeds, database
from utils.config import config
from utils.record import record_usage

log = logging.getLogger(__name__)


class DailyCog(Cog):
    """Daily command cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="daily",
        description="Receives some buffer once every 20 hours",
        guild_ids=config["guild_ids"],
    )
    async def daily(self, ctx: SlashContext):
        """Receives some buffer once every 20 hours."""
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

        # Loads the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user["stats"])

        # Cooldown: 72000s = 20hrs.
        cooldown = 72000

        # Get the current timestamp in Unix.
        current_time = int(time.time())

        # Get the time delta since the last daily claim.
        time_delta = current_time - stats["daily_timestamp"]

        # Condition: True if the time elapsed since last daily claim is larger than the cooldown.
        availability_check = time_delta >= cooldown

        # If any of the conditions were not met, return an error embed.
        if not availability_check:
            # Get the amount of time left until the next daily claim.
            time_remaining = cooldown - time_delta

            # Hours are the time in seconds divided by 3600.
            hours, remainder = divmod(time_remaining, 3600)

            # Minutes are the hour remainder divided by 60. The remainder are the seconds.
            minutes, seconds = divmod(remainder, 60)

            # String that will store the duration in a more digestible format.
            duration_string = ""
            duration = {"hours": hours, "minutes": minutes, "seconds": seconds}

            for time_unit in duration:
                # If the time value is 0, skip it.
                if duration[time_unit] == 0:
                    continue
                # If the time value is 1, make the time unit into singular form.
                if duration[time_unit] == 1:
                    duration_string += f"{duration[time_unit]} {time_unit[:-1]} "
                else:
                    duration_string += f"{duration[time_unit]} {time_unit} "

            # Create the embed and notify the user the amount of time until the next daily claim.
            embed = embeds.make_embed(
                title="Transaction failed",
                description="You can only claim your daily buffer reward once every 20 hours.",
                color="red",
            )
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.add_field(name="​", value=f"**Time remaining:** {duration_string}", inline=False)
            db.close()
            return await ctx.send(embed=embed)

        # Roll a random value from 0-100.
        rng = random.randint(0, 100)

        # 55% chance to roll the common tier.
        if rng in range(0, 56):
            value = random.randint(150, 250)
            description = f"You received {value} MB buffer!"
            color = "soft_green"
        # 30% chance to roll the uncommon tier.
        elif rng in range(56, 86):
            value = random.randint(300, 400)
            description = f"Nice, you received {value} MB buffer!"
            color = "green"
        # 10% chance to roll the rare tier.
        elif rng in range(86, 96):
            value = random.randint(450, 600)
            description = f"Amazing! You received {value} MB buffer!"
            color = "blue"
        # 4% chance to roll the epic tier.
        elif rng in range(96, 100):
            value = random.randint(650, 800)
            description = f"What a fascinating discovery! You received {value} MB buffer!"
            color = "purple"
        # 1% chance to roll the legendary tier.
        else:
            value = random.randint(850, 1024)
            description = f"Whoa?! This is truly exceptional! You received {value} MB buffer!"
            color = "gold"

        # Create the embed with a matching color on rarity rolled, and update tge
        embed = embeds.make_embed(
            title="Daily buffer claimed",
            description=description,
            color=color,
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        # Roll a random float value to determine if /daily is going to be doubled or not.
        double_daily = random.uniform(0, 100)

        # Check if the rolled float value falls within the double range based on daily_upgrade amount and update the value if it does.
        if 0 <= double_daily <= stats["daily_upgrade"] * 0.35:
            value = value * 2
            # Some fluff in the congratulation string.
            words = [
                "brave",
                "bold",
                "strong",
                "wise",
                "ambitious",
                "blind",
                "devil",
                "naive",
                "poor",
                "wanderer",
                "fool",
                "betrayer",
            ]
            embed.add_field(
                name="​",
                value=f"**Fortune favors the {random.choice(words)}:** You received 2x buffer for a total of {value} MB!",
                inline=False,
            )

        # Update the new timestamp and total buffer after the successful daily claim.
        stats["daily_timestamp"] = current_time
        stats["buffer"] += value

        # Get the formatted buffer string.
        buffer_string = await leveling_cog.get_buffer_string(stats["buffer"])
        embed.add_field(name="​", value=f"**Total buffer:** {buffer_string}", inline=False)
        await ctx.send(embed=embed)

        # Dump the modified JSON into the db and close it.
        stats_json = json.dumps(stats)
        economy.update(dict(id=user["id"], stats=stats_json), ["id"])
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """Load the Daily cog."""
    bot.add_cog(DailyCog(bot))
    log.info("Commands loaded: daily")
