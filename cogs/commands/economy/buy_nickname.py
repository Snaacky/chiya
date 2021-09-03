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


class BuyNicknameCog(Cog):
    """ Buy nickname command cog. """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="buy",
        name="nickname",
        description="Purchase a nickname",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="nickname",
                description="The name to be changed to.",
                option_type=3,
                required=True
            ),
            create_option(
                name="freeleech",
                description="Enable freeleech for this item, costing 1 freeleech token.",
                option_type=5,
                required=False
            ),
        ],
    )
    async def buy_nickname(self, ctx: SlashContext, nickname: str, freeleech: bool = False):
        """ Purchase and change the nickname. """
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

        # Load the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user["stats"])

        # Check the integrity of the stats dictionary and add any potential missing keys.
        stats = await leveling_cog.verify_integrity(stats)

        # Cost of the transaction. Declared separately to give less headaches on future balance changes.
        cost = 256
        fl_token = 1

        # Declare the allowed user classes for the custom role purchase.
        allowed_classes = ["User", "Power User", "Elite", "Torrent Master", "Power TM", "Elite TM", "Legend"]

        # Condition: Buffer must be above 256 MB.
        buffer_check = stats["buffer"] >= cost

        # Condition: Must have at least 1 freeleech token.
        fl_token_check = stats["freeleech_token"] >= fl_token

        # Condition: User class must be "User" or higher.
        user_class_check = any(stats["user_class"] == allowed_class for allowed_class in allowed_classes)

        # If any of the conditions were not met, return an error embed.
        if not buffer_check or not fl_token_check or not user_class_check:
            embed = embeds.make_embed(
                title=f"Transaction failed",
                description="One or more of the following conditions were not met:",
                color="red"
            )
            # Dynamically add the reason(s) why the transaction was unsuccessful.
            if not buffer_check:
                embed.add_field(name="Condition:", value=f"You must have at least {await leveling_cog.get_buffer_string(cost)} buffer.", inline=False)
            if not user_class_check:
                embed.add_field(name="Condition:", value="User class must be 'User' or higher.", inline=False)
            if freeleech and not fl_token_check:
                embed.add_field(name="Condition:", value="You don't have enough freeleech token.", inline=False)
            await ctx.send(embed=embed)
            db.close()
            return

        # Send a confirmation embed before proceeding the transaction.
        confirm_embed = embeds.make_embed(color="green")
        if freeleech:
            confirm_embed.description = f"{ctx.author.mention}, set your nickname to '{nickname}' for {fl_token} " \
                                        f"freeleech {'tokens' if fl_token > 1 else 'token'}? (yes/no/y/n)"
        else:
            confirm_embed.description = f"{ctx.author.mention}, set your nickname to '{nickname}' for {cost} MB? (yes/no/y/n)"
        await ctx.send(embed=confirm_embed)

        # A function to check if the reply is "yes", "no", "y", or "n", and is the command's author in the current channel.
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() in ["yes", "no", "y", "n"]

        # Wait for the user's reply (yes/no/y/n) and return if the response is "no", "n" or no response was received after 60s.
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

        # Edit the author's nickname.
        await ctx.author.edit(nick=nickname)

        # Create the embed to let the user know that the transaction was a success.
        embed = embeds.make_embed(title=f"Nickname purchased: {nickname}", color="green")

        # Update the JSON object accordingly with flexible embed description and field.
        if freeleech:
            stats["freeleech_token"] -= fl_token
            embed.description = f"Successfully purchased a nickname for {fl_token} freeleech {'tokens' if fl_token > 1 else 'token'}."
            embed.add_field(name="​", value=f"**Remaining freeleech tokens:** {stats['freeleech_token']}")
        else:
            stats["buffer"] -= cost
            embed.description = f"Successfully purchased a nickname for {cost} MB buffer."
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
    """ Load the BuyNickname cog. """
    bot.add_cog(BuyNicknameCog(bot))
    log.info("Commands loaded: buy_nickname")
