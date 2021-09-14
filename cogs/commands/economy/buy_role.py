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


class BuyRoleCog(Cog):
    """Buy role command cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="buy",
        name="role",
        description="Purchase a role with a specified name",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="name",
                description="The name of the role",
                option_type=3,
                required=True,
            ),
            create_option(
                name="freeleech",
                description="Enable freeleech for this item, costing 5 freeleech tokens",
                option_type=5,
                required=False,
            ),
        ],
    )
    async def buy_role(self, ctx: SlashContext, name: str, freeleech: bool = False):
        """Purchase a role and assign it to themselves."""
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

        # Load the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user["stats"])

        # Cost of the transaction. Declared separately to give less headaches on future balance changes.
        cost = 10240
        fl_token = 5

        # Declare the allowed user classes for the custom role purchase.
        allowed_classes = [
            "Power User",
            "Elite",
            "Torrent Master",
            "Power TM",
            "Elite TM",
            "Legend",
        ]

        # Condition: Buffer must be above 10 GB.
        buffer_check = stats["buffer"] >= cost

        # Condition: Must have at least 5 freeleech tokens.
        fl_token_check = stats["freeleech_token"] >= fl_token

        # Condition: User class must be "Elite" or higher.
        user_class_check = any(
            stats["user_class"] == allowed_class for allowed_class in allowed_classes
        )

        # Condition: Must not already own a custom role.
        custom_role_check = stats["has_custom_role"]

        # If any of the conditions were not met, return an error embed.
        if (
            not buffer_check
            or (freeleech and not fl_token_check)
            or not user_class_check
            or custom_role_check
        ):
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
            if not user_class_check:
                embed.add_field(
                    name="​",
                    value="**Condition:** User class must be 'Power User' or higher.",
                    inline=False,
                )
            if custom_role_check:
                embed.add_field(
                    name="​",
                    value="**Condition:** You must not own a custom role yet.",
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
                f"{ctx.author.mention}, purchase a custom role with the name '{name}' for {fl_token} "
                f"freeleech {'tokens' if fl_token > 1 else 'token'}? (yes/no/y/n)"
            )
        else:
            confirm_embed.description = f"{ctx.author.mention}, purchase a custom role with the name '{name}' for {cost} MB? (yes/no/y/n)"
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

        # Create the role with the desired name, add it to the buyer, and update the JSON. Default is no permission and colorless.
        custom_role = await ctx.guild.create_role(
            name=name, reason="Custom role purchase."
        )
        await ctx.author.add_roles(custom_role)
        stats["custom_role_id"] = custom_role.id

        # Get the role count in the guild.
        role_count = len(ctx.guild.roles)

        # Number of mod roles (including the separator that follows the category). Declared to avoid magic number usage.
        mod_role_count = 13

        # Declare the positions of the role as a dictionary.
        positions = dict()

        """ 
        edit_role_permission() does not have anything to do with @everyone even when it shows up when enumerating guilds.roles,
        and indexing starts from 0 with the bottommost role. https://github.com/Rapptz/discord.py/pull/2501 was implemented as an
        attempt to fix Discord's caching issue by Discord when edit() is called, that would mess up all the other role positions,
        described in https://github.com/Rapptz/discord.py/issues/2142. That said, DO NOT use edit() to edit a role position, or you'll 
        spend 30 minutes to manually fix the mess. Use debug mode to check for the output first.
        """

        # Iterate and enumerate all the roles in the guild.
        for index, role in enumerate(ctx.guild.roles):
            # Skip @everyone and the newly added role and add it back into the correct hierarchy later.
            if index <= 1:
                continue
            # Push down all the roles before the mod roles index value by 2 to make up for the skipped values.
            elif index < role_count - mod_role_count:
                positions[index - 2] = role
            # From the first mod role (the category separator), bump all the roles up by 1 to make a space for the new role.
            else:
                positions[index - 1] = role

        # Finally, add the custom role to the location between the two category separator roles.
        positions[role_count - mod_role_count - 2] = custom_role

        # Inverse the key pair value of the dictionary before using it to edit the position of all roles in the guild.
        positions = dict((value, key) for key, value in positions.items())
        await ctx.guild.edit_role_positions(
            positions=positions, reason="Custom role purchased."
        )

        # Create the embed to let the user know that the transaction was a success.
        embed = embeds.make_embed(
            title=f"Role purchased: {custom_role.name}", color="green"
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        # Update the JSON object accordingly with flexible embed description and field.
        if freeleech:
            stats["freeleech_token"] -= fl_token
            embed.description = f"Successfully purchased a custom role for {fl_token} freeleech {'tokens' if fl_token > 1 else 'token'}."
            embed.add_field(
                name="​",
                value=f"**Remaining freeleech tokens:** {stats['freeleech_token']}",
            )
        else:
            stats["buffer"] -= cost
            embed.description = (
                f"Successfully purchased a custom role for {cost} MB buffer."
            )
            # Get the formatted buffer string.
            buffer_string = await leveling_cog.get_buffer_string(stats["buffer"])
            embed.add_field(name="​", value=f"**New buffer:** {buffer_string}")

        stats["has_custom_role"] = True

        await ctx.send(embed=embed)

        # Dump the modified JSON into the db and close it.
        stats_json = json.dumps(stats)
        achievements.update(dict(id=user["id"], stats=stats_json), ["id"])
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """Load the BuyRole cog."""
    bot.add_cog(BuyRoleCog(bot))
    log.info("Commands loaded: buy_role")
