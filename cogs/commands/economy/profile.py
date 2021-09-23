import json
import logging

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

from cogs.commands import settings
from utils import embeds, database
from utils.record import record_usage

log = logging.getLogger(__name__)


class ProfileCog(Cog):
    """Profile command cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="profile",
        description="View your profile",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="user",
                description="The profile of the specified user",
                option_type=6,
                required=False,
            )
        ],
    )
    async def profile(self, ctx: SlashContext, user: discord.User = None):
        """View personal profile with detailed stats."""
        await ctx.defer()

        # Warn if the command is called outside of #bots channel. Using a tuple is more memory efficient.
        if ctx.channel.id not in (
            settings.get_value("channel_bots"),
            settings.get_value("channel_bot_testing"),
        ):
            return await embeds.error_message(ctx=ctx, description="This command can only be run in #bots channel.")

        # The user is either the author or the specified user in the parameter.
        user = user or ctx.author

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        # Get the LevelingCog for utilities functions.
        leveling_cog = self.bot.get_cog("LevelingCog")

        # Connect to the database and get the achievement table.
        db = dataset.connect(database.get_db())
        achievements = db["achievements"]

        # Attempt to find the user who issued the command.
        user_entry = achievements.find_one(user_id=user.id)

        # If the user is not found, initialize their entry, insert it into the db and get their entry which was previously a NoneType.
        if not user_entry:
            stats_json = await leveling_cog.create_user()
            achievements.insert(dict(user_id=user.id, stats=stats_json))
            user_entry = achievements.find_one(user_id=user.id)

        # Loads the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user_entry["stats"])

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

        # Get the role from user's custom role ID to get its color if they have one. Otherwise, default the color to "green".
        role = discord.utils.get(ctx.guild.roles, id=stats["custom_role_id"])
        color = role.color if role else "green"
        custom_role = role.mention if role else "None"
            
        # Declare the value parameter for the embed. Doing it this way allows the name and value displayed on a single line.
        value = (
            f"**User class:** {stats['user_class']}\n\n"
            f"**Double daily:** Level {stats['daily_upgrade']} (+{round(stats['daily_upgrade'] * 0.35, 2)}%)\n"
            f"**Saturation:** Level {stats['saturation_upgrade']}\n"
            f"**Brightness:** Level {stats['value_upgrade']}\n"
            f"**Purchased color packs:** {color_packs}\n"
            f"**Vouches received:** {stats['vouch']}\n"
            f"**Freeleech tokens:** {stats['freeleech_token']}\n\n"
            f"**Custom role:** {custom_role}\n\n"
            f"**Buffer:** {buffer_string}"
        )

        # Create the embed.
        embed = embeds.make_embed(
            color=color,
            thumbnail_url=user.avatar_url,
        )

        # Display the user's minified pfp and their name without the discriminator.
        embed.set_author(name=f"{user.name}'s profile", icon_url=user.avatar_url)

        # Using zero width space so that the "name" parameter won't be rendered.
        embed.add_field(name="​", value=value, inline=False)

        # Display the buffer percentage until the next user class. Default the percentage to 0 if the divisor is 0.
        buffer_percentage = (
            round(stats["buffer"] / stats["next_user_class_buffer"] * 100, 2)
            if stats["next_user_class_buffer"] != 0
            else 0
        )
        # Display the amount of buffer required until next promotion.
        embed.add_field(
            name="Buffer required for promotion:",
            value=f"{buffer_string} / {next_class_buffer_string} ({buffer_percentage}%)",
            inline=False,
        )

        # Display the message percentage until the next user class. Default the percentage to 0 if the divisor is 0.
        message_percentage = (
            round(stats["message_count"] / stats["next_user_class_message"] * 100, 2)
            if stats["next_user_class_message"] != 0
            else 0
        )
        # Display the amount of "uploads" required until next promotion. Default the percentage to 0 if the divisor is 0.
        embed.add_field(
            name="Uploads required for promotion:",
            value=f"{stats['message_count']} / {stats['next_user_class_message']} ({message_percentage}%)",
            inline=False,
        )

        # Send the embed and close the connection. No commit is needed because nothing is changed.
        await ctx.send(embed=embed)
        db.close()


def setup(bot: Bot) -> None:
    """Load the Profile cog."""
    bot.add_cog(ProfileCog(bot))
    log.info("Commands loaded: profile")
