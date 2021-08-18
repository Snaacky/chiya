import json
import logging
import random

import dataset
import discord.utils
from discord import Message, Member
from discord.ext import commands
from discord.ext.commands import Bot, Cog

from cogs.commands import settings
from utils import database

log = logging.getLogger(__name__)


class LevelingCog(Cog):
    """ Leveling cog. """

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        """ The entry point for buffer calculation and promotion/demotion on every messages sent. """

        # If the author is a bot, skip them.
        if message.author.bot:
            return

        # Connect to the database and get the achievement table.
        db = dataset.connect(database.get_db())
        achievements = db["achievements"]
        user = achievements.find_one(user_id=message.author.id)

        # If the user is not found, initialize their entry, insert it into the db and get their entry which was previously a NoneType.
        if not user:
            stats_json = await self.create_user()
            achievements.insert(dict(user_id=message.author.id, stats=stats_json))
            user = achievements.find_one(user_id=message.author.id)

        # Load the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user["stats"])

        # Increment the message count.
        stats["message_count"] += 1

        channel_enabled = await self.is_in_enabled_channels(message=message)
        if channel_enabled:
            # Calculate their buffer to be gained as well as a potential user class promotion/demotion. Returns a JSON object.
            stats_json = await self.calculate_buffer(message, stats)
            # Update the user stats in the database.
            achievements.update(dict(id=user["id"], stats=stats_json), ["id"])

        # Commit the changes to the database and close it.
        db.commit()
        db.close()

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        """ Automatically add the user's custom role back if possible. """
        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        # Get the user that just joined.
        achievements = db["achievements"]
        user = achievements.find_one(user_id=member.id)

        # If the user is found, load the JSON object in the database into a dictionary.
        if user:
            stats = json.loads(user["stats"])
            # Check if such user has a custom role. If true, get it and add it back to them.
            if stats["has_custom_role"]:
                role_custom = discord.utils.get(member.guild.roles, id=stats["custom_role_id"])
                await member.add_roles(role_custom)

        # Close the connection.
        db.close()

    @staticmethod
    async def calculate_buffer(message: Message, stats):
        """ Calculate the amount of buffers gained from messages and promote/demote conditionally. """

        # Get the number of words in a message.
        length = len(message.content.split())

        # Heavily punishes emote spams, links, gifs, etc.
        if length in range(0, 3):
            multiplier = 0.33
        # Discourage very short messages.
        elif length in range(3, 5):
            multiplier = 0.67
        # Slightly punish short messages.
        elif length in range(5, 8):
            multiplier = 0.9
        # Normal multiplier to average messages.
        elif length in range(8, 11):
            multiplier = 1
        # Slightly encourages longer messages.
        elif length in range(11, 16):
            multiplier = 1.1
        # Further encourages long messages.
        else:
            multiplier = 1.2

        # Calculate the baseline buffer.
        buffer = length * multiplier

        # If the message author is a server booster, give them 20% more buffer per message.
        role_server_booster = discord.utils.get(message.guild.roles, id=settings.get_value("role_server_booster"))
        is_booster = True if role_server_booster in message.author.roles else False
        if is_booster:
            buffer = buffer + buffer * 0.2

        # Set a max cap to prevent abuse (low effort copy paste, trolling, copypasta, etc.)
        if buffer <= 40:
            stats["buffer"] += buffer
        else:
            stats["buffer"] += 40

        # Demoted to "Member" if buffer is smaller than 10 GB.
        if stats["buffer"] < 10240:
            stats["user_class"] = "Member"
        # Promotes to "User" if buffer is above 10 GB, but demotes to it if below 25 GB. At least 1000 messages are required.
        elif stats["buffer"] < 25600 and stats["message_count"] >= 1000:
            stats["user_class"] = "User"
        # Promotes to "Power User" if buffer is above 25 GB, but demotes to it if below 50 GB. At least 2,500 messages are required.
        elif stats["buffer"] < 51200 and stats["message_count"] >= 2500:
            stats["user_class"] = "Power User"
        # Promotes to "Elite" if buffer is above 50 GB, but demotes to it if below 100 GB. At least 5,500 messages are required.
        elif stats["buffer"] < 102400 and stats["message_count"] >= 5000:
            stats["user_class"] = "Elite"
        # Promotes to "Torrent Master" if buffer is above 100 GB, but demotes to it if below 250 GB. At least 10,000 messages are required.
        elif stats["buffer"] < 256000 and stats["message_count"] >= 10000:
            stats["user_class"] = "Torrent Master"
        # Promotes to "Power TM" if buffer is above 250 GB, but demotes to it if below 500 GB. At least 22,500 messages are required.
        elif stats["buffer"] < 512000 and stats["message_count"] >= 22500:
            stats["user_class"] = "Power TM"
        # Promotes to "Elite TM" if buffer is above 500 GB, but demotes to it if below 1 TB. At least 45,000 messages are required.
        elif stats["buffer"] < 1048576 and stats["message_count"] >= 45000:
            stats["user_class"] = "Elite TM"
        # Promotes to "Legend" if buffer is above 1 TB. At least 80,000 messages are required.
        elif stats["buffer"] >= 1048576 and stats["message_count"] >= 80000:
            stats["user_class"] = "Legend"

        # Dump the manipulated dictionary into a JSON object and return it.
        stats_json = json.dumps(stats)
        return stats_json

    @staticmethod
    async def create_user():
        """ Initialize the JSON object for user stats if it doesn't exist yet. """

        # Initialize the user's entry in the database.
        stats = {
            "user_class": "Member",
            "message_count": 0,
            "buffer": 0,
            "freeleech_token": 0,
            "has_custom_role": False,
            "custom_role_id": 0,
            "hue_upgrade": [],
            "saturation_upgrade": 0,
            "value_upgrade": 0,
            "achievements": []
        }
        # Dump the string into a JSON object and return it.
        stats_json = json.dumps(stats)
        return stats_json

    @staticmethod
    async def is_in_enabled_channels(message: Message) -> bool:
        """ Check if the sent message is from one of the enabled channels or not. """

        # Get all categories from the guild.
        categories = message.guild.categories

        # Return true if the message was sent any channel under the community category.
        if any(message.channel.category.id == settings.get_value("category_community") for category in categories):
            return True

        # Return true if the message was sent in #mudae-lounge.
        if message.channel.id == settings.get_value("channel_mudae_lounge"):
            return True

        # TODO: Remove this on production. This is solely for testing convenience purpose.
        if message.channel.id == settings.get_value("channel_bots"):
            return True

        # Return false otherwise.
        return False

    @staticmethod
    async def get_buffer_string(buffer) -> str:
        """ Display the buffer in a beautified format of MB, GB, and TB. """
        # If buffer is larger than 1024 GB, display it in TB instead.
        if buffer >= 1024 ** 2:
            buffer_string = f"{round(buffer / (1024 ** 2), 2)} TB"
        # Else if buffer is larger than 1024 MB, display it in GB instead.
        elif buffer >= 1024:
            buffer_string = f"{round(buffer / 1024, 2)} GB"
        # Otherwise, display it in MB.
        else:
            buffer_string = f"{round(buffer, 2)} MB"

        # Finally, return the formatted string.
        return buffer_string

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


def setup(bot: Bot) -> None:
    """ Load the Leveling cog. """
    bot.add_cog(LevelingCog(bot))
    log.info("Commands loaded: leveling")
