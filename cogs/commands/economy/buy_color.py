import json
import logging
import random

import dataset
import discord.utils
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext

from cogs.commands import settings
from utils import embeds, database
from utils.record import record_usage

log = logging.getLogger(__name__)


class BuyColorCog(Cog):
    """ Buy color command cog. """

    def __init__(self, bot: Bot):
        self.bot = bot

    @staticmethod
    async def generate_hsv(hue_upgrade: list, saturation_upgrade: int, value_upgrade: int) -> tuple:
        """ Generates a random HSV tuple affected by the purchased upgrades. """
        # Declare a list of possible color packs.
        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]

        # Create a dictionary that maps the color pack name with the range of roll values, unpacked into a list with the * operator.
        color_map = dict(
            # Red-like colors span from 331-360 and 1-30 degrees on the HSV scale.
            red=[*range(331, 361), *range(1, 31)],
            # Yellow-like colors span from 31-90 degrees on the HSV scale.
            yellow=[*range(31, 91)],
            # Green-like colors span from 91-150 degrees on the HSV scale.
            green=[*range(91, 151)],
            # Cyan-like colors span from 151-210 degrees on the HSV scale.
            cyan=[*range(151, 211)],
            # Blue-like colors span from 211-270 degrees on the HSV scale.
            blue=[*range(211, 271)],
            # Magenta-like colors span from 271-330 degrees on the HSV scale.
            magenta=[*range(271, 331)]
        )

        # Declare an empty list to append the roll values later.
        hue = list()

        # Iterate through the input parameter that is a list of purchased color packs.
        for pack in hue_upgrade:
            # If one of the options matches one of the strings in "colors", append to the list of roll values range from the dictionary.
            if pack in colors:
                hue += color_map[pack]

        """
        Hue, saturation, and value is divided by 360, 100, 100 accordingly because it is using the fourth coordinate group described in
        https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Color/Normalized_Color_Coordinates#HSV_coordinates.
        This was not clarified in https://discordpy.readthedocs.io/en/latest/api.html?highlight=from_hsv#discord.Colour.from_hsv.
        """
        # Finally, return random HSV tuple, affected by the purchased upgrades.
        return \
            random.choice(hue) / 360, \
            random.randint(0, saturation_upgrade + 1) / 100, \
            random.randint(0, value_upgrade + 1) / 100

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="buy",
        name="color",
        description="Roll for a random role color",
        guild_ids=[settings.get_value("guild_id")],
    )
    async def buy_color(self, ctx: SlashContext):
        """ Roll a random role color using buffer. """
        await ctx.defer()

        # Get the LevelingCog for utilities functions.
        leveling_cog = self.bot.get_cog("LevelingCog")

        # Warn if the command is called outside of #bots channel.
        if not ctx.channel.id == settings.get_value("channel_bots"):
            await embeds.error_message(ctx=ctx, description="You can only run this command in #bots channel.")
            return

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

        # Cost of the transaction. Declared separately to give less headaches on future balance changes.
        cost = 128

        # Condition: Buffer must be above 128 MB.
        buffer_check = bool(stats["buffer"] >= cost)

        # Condition: Must have purchased at least 1 color pack.
        if len(stats["hue_upgrade"]) == 0:
            color_check = False
        else:
            color_check = True

        # Condition: Must already own a custom role.
        custom_role_check = stats["has_custom_role"]

        # If any of the conditions were not met, return an error embed.
        if not buffer_check or not color_check or not custom_role_check:
            embed = embeds.make_embed(
                ctx=ctx,
                title="Transaction failed",
                description="One or more of the following conditions were not met:",
                color="red"
            )
            # Dynamically add the reason(s) why the transaction was unsuccessful.
            if not buffer_check:
                embed.add_field(name="Condition:", value=f"You must have at least {await leveling_cog.get_buffer_string(cost)} buffer.", inline=False)
            if not color_check:
                embed.add_field(name="Condition:", value="You must have purchased at least one color pack.", inline=False)
            if not custom_role_check:
                embed.add_field(name="Condition:", value="You must own a custom role.", inline=False)
            await ctx.send(embed=embed)
            db.close()
            return

        # Generates a HSV color from the purchased color packs, saturation and value upgrade.
        hue, saturation, value = await self.generate_hsv(stats["hue_upgrade"], stats["saturation_upgrade"], stats["value_upgrade"])
        color = discord.Color.from_hsv(hue, saturation, value)

        # Get the role from user's custom role ID to edit the color.
        role = discord.utils.get(ctx.guild.roles, id=stats["custom_role_id"])
        await role.edit(color=color)

        # Update the JSON object accordingly.
        stats["buffer"] -= cost

        # Get the formatted buffer string.
        buffer_string = await leveling_cog.get_buffer_string(stats["buffer"])

        # Create an embed with the rolled color upon successful transaction.
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"You rolled: {color}",
            color=color
        )
        embed.add_field(name="New buffer:", value=buffer_string)
        await ctx.send(embed=embed)

        # Dump the modified JSON into the db and close it.
        stats_json = json.dumps(stats)
        achievements.update(dict(id=user["id"], stats=stats_json), ["id"])

        # Commit the changes to the database and close it.
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """ Load the BuyColor cog. """
    bot.add_cog(BuyColorCog(bot))
    log.info("Commands loaded: buy_color")
