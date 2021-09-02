import json
import logging
import random
import time

import dataset
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext

from cogs.commands import settings
from utils import embeds, database
from utils.record import record_usage

log = logging.getLogger(__name__)


class DailyCog(Cog):
    """ Daily command cog. """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="daily",
        description="Receives some buffer once every 20 hours",
        guild_ids=[settings.get_value("guild_id")],
    )
    async def daily(self, ctx: SlashContext):
        """ Receives some buffer once every 20 hours. """
        await ctx.defer()

        # Warn if the command is called outside of #bots channel.
        if not ctx.channel.id == settings.get_value("channel_bots"):
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
            duration = {
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds
            }

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
                color="red"
            )
            embed.add_field(name="Time remaining:", value=duration_string, inline=False)
            await ctx.send(embed=embed)
            db.close()
            return

        # Roll a random value from 0-100.
        rng = random.randint(0, 100)

        # Create the embed with a matching color on rarity rolled, and update tge
        embed = embeds.make_embed(
            title="Daily buffer claimed",
        )
        # 55% chance to roll the common tier. Embed color is "soft_green".
        if rng in range(0, 56):
            value = random.randint(150, 250)
            embed.description = f"You received {value} MB buffer!"
            embed.colour = 0x68c290
        # 30% chance to roll the uncommon tier. Embed color is "green".
        elif rng in range(56, 86):
            value = random.randint(300, 400)
            embed.description = f"Nice, you received {value} MB buffer!"
            embed.colour = 0x2ecc71
        # 10% chance to roll the rare tier. Embed color is "blue".
        elif rng in range(86, 96):
            value = random.randint(450, 600)
            embed.description = f"Amazing! You received {value} MB buffer!"
            embed.colour = 0x3498db
        # 4% chance to roll the epic tier. Embed color is "purple".
        elif rng in range(96, 100):
            value = random.randint(650, 800)
            embed.description = f"What a fascinating discovery! You received {value} MB buffer!"
            embed.colour = 0x9b59b6
        # 1% chance to roll the legendary tier. Embed color is "gold".
        else:
            value = random.randint(850, 1024)
            embed.description = f"Whoa?! This is truly exceptional! You received {value} MB buffer!"
            embed.colour = 0xf1c40f

        # Roll a random float value to determine if /daily is going to be doubled or not.
        double_daily = random.uniform(0, 100)

        # Check if the rolled float value falls within the double range based on daily_upgrade amount and update the value if it does.
        if 0 <= double_daily <= stats["daily_upgrade"] * 0.3:
            value = value * 2
            # Some fluff in the congratulation string.
            words = ["brave", "bold", "strong", "wise", "ambitious", "blind", "devil", "naive", "poor", "wanderer", "fool", "betrayer"]
            embed.add_field(
                name="​",
                value=f"**Fortune favors the {random.choice(words)}**: You received 2x buffer for a total of {value} MB!",
                inline=False
            )

        # Update the new timestamp and total buffer after the successful daily claim.
        stats["daily_timestamp"] = current_time
        stats["buffer"] += value

        # Get the formatted buffer string.
        buffer_string = await leveling_cog.get_buffer_string(stats["buffer"])
        embed.add_field(name="Total buffer:", value=buffer_string, inline=False)
        await ctx.send(embed=embed)

        # Dump the modified JSON into the db.
        stats_json = json.dumps(stats)
        achievements.update(dict(id=user["id"], stats=stats_json), ["id"])

        # Commit the changes to the database and close it.
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """ Load the Daily cog. """
    bot.add_cog(DailyCog(bot))
    log.info("Commands loaded: daily")
