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


class UpgradeSaturationCog(Cog):
    """ Upgrade saturation command cog. """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="upgrade",
        name="saturation",
        description="Allows more saturated colors to be rolled",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="amount",
                description="Number of upgrades to purchase. ",
                option_type=4,
                required=True
            ),
        ],
    )
    async def upgrade_saturation(self, ctx: SlashContext, amount: int):
        """ Allows more saturated colors to be rolled. """
        await ctx.defer()

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

        # The actual cost for the purchase is 3 * x (x is from 1-100) - it gets more expensive after every upgrade.
        inflated_cost = stats["saturation_upgrade"] * cost + amount * cost

        # Condition: Must have more buffer than the cost of the transaction.
        buffer_check = bool(stats["buffer"] >= inflated_cost)

        # Condition: Must have purchased at least 1 color pack.
        if len(stats["hue_upgrade"]) == 0:
            color_check = False
        else:
            color_check = True

        # Condition: The total number of upgrades must not exceed 100.
        availability_check = True if amount + stats["saturation_upgrade"] <= 100 else False

        # Condition: Must already own a custom role.
        custom_role_check = stats["has_custom_role"]

        # If any of the conditions were not met, return an error embed.
        if not buffer_check or not color_check or not availability_check or not custom_role_check:
            embed = embeds.make_embed(
                ctx=ctx,
                title="Transaction failed",
                description="One or more of the following conditions were not met:",
                color="red"
            )
            # Dynamically add the reason(s) why the transaction was unsuccessful.
            if not buffer_check:
                embed.add_field(name="Condition:", value=f"You must have at least {await leveling_cog.get_buffer_string(inflated_cost)} buffer.", inline=False)
            if not color_check:
                embed.add_field(name="Condition:", value="You must have purchased at least one color pack.", inline=False)
            if not custom_role_check:
                embed.add_field(name="Condition:", value="You must own a custom role.", inline=False)
            if not availability_check:
                embed.add_field(name="Condition:", value=f" You can only purchase this upgrade {100 - stats['saturation_upgrade']} more times!", inline=False)
            await ctx.send(embed=embed)
            db.close()
            return

        # Update the JSON object.
        stats["saturation_upgrade"] += inflated_cost

        # Get the formatted buffer string.
        buffer_string = await leveling_cog.get_buffer_string(stats["buffer"])

        # Create an embed upon successful transaction.
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Upgrade purchased: saturation",
            description=f"You reached saturation level {stats['saturation_upgrade']}!",
            color="green"
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
    """ Load the UpgradeSaturation cog. """
    bot.add_cog(UpgradeSaturationCog(bot))
    log.info("Commands loaded: upgrade_saturation")
