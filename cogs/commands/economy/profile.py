import json
import logging

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext

from cogs.commands import settings
from utils import embeds, database
from utils.record import record_usage

log = logging.getLogger(__name__)


class ProfileCog(Cog):
    """ Profile command cog. """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="profile",
        description="View your profile",
        guild_ids=[settings.get_value("guild_id")],
    )
    async def daily(self, ctx: SlashContext):
        """ View personal profile with detailed stats. """
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

        # Append the purchased colors into the string if the user has one.
        color_packs = ""
        if len(stats["hue_upgrade"]) > 0:
            for color in sorted(stats["hue_upgrade"]):
                color_packs += f"{color}, "
            # Remove the trailing comma and white space after appending.
            color_packs = color_packs[:-2]
        else:
            color_packs = "None"

        # Display the buffer into a more digestible format.
        buffer_string = await leveling_cog.get_buffer_string(stats["buffer"])
        next_class_buffer_string = await leveling_cog.get_buffer_string(stats["next_user_class_buffer"])

        # Get the role from user's custom role ID to get its color if they have one. Otherwise, default it to "green".
        if stats["has_custom_role"]:
            role = discord.utils.get(ctx.guild.roles, id=stats["custom_role_id"])
            color = role.color
            custom_role = role.mention
        else:
            color = 0x2ecc71
            custom_role = "None"

        # Declare the value parameter for the embed. Doing it this way allows the name and value displayed on a single line.
        value = f"**User class:** {stats['user_class']}\n\n" \
                f"**Saturation:** Level {stats['saturation_upgrade']}\n" \
                f"**Brightness:** Level {stats['value_upgrade']}\n" \
                f"**Purchased color packs:** {color_packs}\n" \
                f"**Vouches received:** {stats['vouch']}\n" \
                f"**Freeleech token:** {stats['freeleech_token']}\n\n" \
                f"**Custom role:** {custom_role}\n\n" \
                f"**Buffer:** {buffer_string}"

        # Create the embed.
        embed = embeds.make_embed(
            color=color,
        )

        # Display the user's minified pfp and their name without the discriminator.
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        # Using zero width space so that the "name" parameter won't be rendered.
        embed.add_field(name="​", value=value, inline=False)

        # Display the amount of buffer required until next promotion.
        embed.add_field(
            name="Buffer required for promotion:",
            value=f"{buffer_string} / {next_class_buffer_string}",
            inline=False
        )

        # Display the amount of "uploads" required until next promotion.
        embed.add_field(
            name="Uploads required for promotion:",
            value=f"{stats['message_count']} / {stats['next_user_class_message']}",
            inline=False
        )

        # Send the embed and close the connection. No commit is needed because nothing is changed.
        await ctx.send(embed=embed)
        db.close()


def setup(bot: Bot) -> None:
    """ Load the Profile cog. """
    bot.add_cog(ProfileCog(bot))
    log.info("Commands loaded: profile")
