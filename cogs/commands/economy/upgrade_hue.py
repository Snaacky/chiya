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


class UpgradeHueCog(Cog):
    """Upgrade hue command cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="upgrade",
        name="hue",
        description="Increase the amount of possible colors that you can roll.",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="pack",
                description="Red, yellow, green, cyan, blue, magenta.",
                option_type=3,
                required=True,
            ),
            create_option(
                name="freeleech",
                description="Enable freeleech for this item, costing 2 freeleech tokens per level.",
                option_type=5,
                required=False,
            ),
        ],
    )
    async def upgrade_hue(self, ctx: SlashContext, pack: str, freeleech: bool = False):
        """Purchase a color pack to increase the amount of possible colors that can be rolled."""
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

        # Purchasable color pack options.
        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]

        # Cost of the transaction. Declared separately to give less headaches on future balance changes.
        cost = 3072
        fl_token = 2

        # Condition: The input color pack choice must match at least one of the items in the allowed colors.
        color_check = any(pack == color for color in colors)

        # Condition: Must not already own the color pack yet.
        owned_check = any(pack == color for color in stats["hue_upgrade"])

        # Condition: Buffer must be above 3 GB.
        buffer_check = stats["buffer"] >= cost

        # Condition: Must have at least 1 freeleech token.
        fl_token_check = stats["freeleech_token"] >= fl_token

        # Condition: Must already own a custom role.
        custom_role_check = stats["has_custom_role"]

        # If any of the conditions were not met, return an error embed.
        if (
            not color_check
            or owned_check
            or not buffer_check
            or (freeleech and not fl_token_check)
            or not custom_role_check
        ):
            embed = embeds.make_embed(
                title="Transaction failed",
                description="One or more of the following conditions were not met:",
                color="red",
            )
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

            # Dynamically add the reason(s) why the transaction was unsuccessful.
            if not color_check:
                embed.add_field(
                    name="Condition:",
                    value="Color pack must be one the following options: red, yellow, green, cyan, blue, magenta.",
                    inline=False,
                )
            if owned_check:
                embed.add_field(
                    name="Condition:",
                    value="You must not already owned the color pack yet.",
                )
            if not buffer_check:
                embed.add_field(
                    name="Condition:",
                    value=f"You must have at least {await leveling_cog.get_buffer_string(cost)} buffer.",
                    inline=False,
                )
            if not custom_role_check:
                embed.add_field(
                    name="Condition:", value="You must own a custom role.", inline=False
                )
            if freeleech and not fl_token_check:
                embed.add_field(
                    name="Condition:",
                    value="You don't have enough freeleech token.",
                    inline=False,
                )
            await ctx.send(embed=embed)
            db.close()
            return

        # Send a confirmation embed before proceeding the transaction.
        confirm_embed = embeds.make_embed(color="green")
        if freeleech:
            confirm_embed.description = (
                f"{ctx.author.mention}, purchase the {pack} color pack for {fl_token} "
                f"freeleech {'tokens' if fl_token > 1 else 'token'}? (yes/no/y/n)"
            )
        else:
            confirm_embed.description = f"{ctx.author.mention}, purchase the {pack} color pack for {cost} MB? (yes/no/y/n)"
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

        # If the input color choice matches any of the items in the purchasable colors, update the JSON object.
        if any(pack == color for color in colors):
            stats["hue_upgrade"].append(pack)

        # Create an embed upon successful transaction.
        embed = embeds.make_embed(
            title=f"Color unlocked: {str(pack)}",
            description=f"You can now roll {pack}-like colors.",
            color="green",
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        # Update the JSON object accordingly with flexible embed description and field.
        if freeleech:
            stats["freeleech_token"] -= fl_token
            embed.add_field(
                name="​",
                value=f"**Remaining freeleech tokens:** {stats['freeleech_token']}",
            )
        else:
            stats["buffer"] -= cost
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
    """Load the UpgradeHue cog."""
    bot.add_cog(UpgradeHueCog(bot))
    log.info("Commands loaded: upgrade_hue")
