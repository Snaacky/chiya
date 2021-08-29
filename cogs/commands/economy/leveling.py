import json
import logging

import dataset
import discord.utils
from discord import Message, Member
from discord.ext import commands
from discord.ext.commands import Bot, Cog

from cogs.commands import settings
from utils import database, embeds

log = logging.getLogger(__name__)

""" 
Declare all the dictionaries as global variable to improve efficiency and better reusability instead of declaring it every time
a message is sent. Declaring a dictionary using literal syntax {} instead of dict() is significantly more efficient.
See: http://katrin-affolter.ch/Python/Python_dictionaries
"""

user_class = {
    "member": "Member",
    "user": "User",
    "power_user": "Power User",
    "elite": "Elite",
    "torrent_master": "Torrent Master",
    "power_tm": "Power TM",
    "elite_tm": "Elite TM",
    "legend": "Legend"
}

buffer_requirement = {
    "member": 0,
    "user": 10240,
    "power_user": 25600,
    "elite": 51200,
    "torrent_master": 102400,
    "power_tm": 256000,
    "elite_tm": 512000,
    "legend": 1048576
}

message_requirement = {
    "member": 0,
    "user": 1000,
    "power_user": 2500,
    "elite": 5000,
    "torrent_master": 10000,
    "power_tm": 22500,
    "elite_tm": 45000,
    "legend": 80000
}

# The user stats template.
stats_template = {
    "user_class": "Member",
    "previous_user_class": "None",
    "next_user_class": "User",
    "buffer": 0,
    "next_user_class_buffer": 0,
    "message_count": 0,
    "next_user_class_message": 0,
    "freeleech_token": 0,
    "vouch": 0,
    "has_custom_role": False,
    "custom_role_id": 0,
    "hue_upgrade": [],
    "saturation_upgrade": 0,
    "value_upgrade": 0,
    "daily_timestamp": 0,
    "achievements": []
}


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

        # Check the integrity of the stats dictionary and add any potential missing keys.
        stats = await self.verify_integrity(stats)

        # Increment the message count.
        stats["message_count"] += 1

        # Calculate buffer gain only in allowed channels.
        channel_enabled = await self.is_in_enabled_channels(message=message)
        if channel_enabled:
            # Calculate the amount of buffer to be gained as well as a potential user class promotion/demotion. Returns a JSON object.
            stats = await self.calculate_buffer(message, stats)
            # Dump the modified JSON into the db.
            stats_json = json.dumps(stats)
            achievements.update(dict(id=user["id"], stats=stats_json), ["id"])

        # Commit the changes to the database and close it.
        db.commit()
        db.close()

    @commands.Cog.listener()
    async def on_message_edit(self, message_before, message_after):
        """ Change the earned buffer on message edit. """
        # If the author is a bot, skip them.
        if message_before.author.bot:
            return

        # Connect to the database and get the achievement table.
        db = dataset.connect(database.get_db())
        achievements = db["achievements"]
        user = achievements.find_one(user_id=message_before.author.id)

        # If the user is not found, initialize their entry, insert it into the db and get their entry which was previously a NoneType.
        if not user:
            stats_json = await self.create_user()
            achievements.insert(dict(user_id=message_before.author.id, stats=stats_json))
            user = achievements.find_one(user_id=message_before.author.id)

        # Load the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user["stats"])

        # Calculate buffer gain only in allowed channels.
        channel_enabled = await self.is_in_enabled_channels(message=message_before)
        if channel_enabled:
            # Remove the buffer gained from the message pre-edit.
            stats_old = await self.calculate_buffer_remove(message_before, stats)
            # Calculate the buffer gained from the newly edited message.
            stats_new = await self.calculate_buffer(message_after, stats_old)
            # Dump the modified JSON into the db.
            stats_json = json.dumps(stats_new)
            achievements.update(dict(id=user["id"], stats=stats_json), ["id"])

        # Commit the changes to the database and close it.
        db.commit()
        db.close()

    @commands.Cog.listener()
    async def on_message_delete(self, message: Message):
        """ Remove the earned buffer on message delete. """
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

        # Decrement the message count.
        stats["message_count"] -= 1

        # Calculate buffer gain only in allowed channels.
        channel_enabled = await self.is_in_enabled_channels(message=message)
        if channel_enabled:
            # Revert the amount of buffer gained. Returns a JSON object.
            stats = await self.calculate_buffer_remove(message, stats)
            # Dump the modified JSON into the db.
            stats_json = json.dumps(stats)
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
        """ Calculate the amount of buffer gained from messages and promote/demote conditionally. """

        # Get the number of words in a message.
        length = len(message.content.split())

        # Heavily punishes emote spams, links, gifs, etc.
        if length in range(0, 2):
            multiplier = 0.33
        # Discourage very short messages.
        elif length in range(2, 4):
            multiplier = 0.67
        # Slightly punish short messages.
        elif length in range(4, 7):
            multiplier = 0.9
        # Normal multiplier to average messages.
        elif length in range(7, 11):
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
        is_booster = role_server_booster in message.author.roles
        if is_booster:
            buffer = buffer + buffer * 0.2

        # Set a max cap to prevent abuse (low effort copy paste, trolling, copypasta, etc.)
        if buffer <= 40:
            stats["buffer"] += buffer
        else:
            stats["buffer"] += 40

        # Make an embed to be sent on user promotion and let them know that they were rewarded a FL token.
        promote_embed = embeds.make_embed(
            title="Promoted!",
            description=f"{message.author.mention} has been promoted to {stats['next_user_class']}!",
            thumbnail_url=message.author.avatar_url,
            color="green"
        )
        promote_embed.add_field(name="​", value="**Reward:** 1x FL Token")

        # Make an embed to be sent on user demotion.
        demote_embed = embeds.make_embed(
            title="Demoted!",
            description=f"{message.author.mention} has been demoted to {stats['previous_user_class']}!",
            thumbnail_url=message.author.avatar_url,
            color="red"
        )

        """ 
        On every message, attempt to compare their current user class with their previous and next user class to be promoted 
        or demoted to. If their current user class equals to the previous user class, it means that they just got demoted,
        and vice versa when promoted. Their previous, current, and next user class will be updated regardlessly. Note that for 
        "Member" class, we don't check for promotion because this is the lowest possible user class. The same applies to the 
        "Legend" class where demotion is not checked because it is the highest possible user class.
        """

        # "Member" if buffer is between 0-10 GB and message count is >= 0.
        if buffer_requirement["member"] <= stats["buffer"] < buffer_requirement["user"] \
                and stats["message_count"] >= message_requirement["member"]:
            stats["user_class"] = user_class["member"]
            stats["next_user_class_buffer"] = buffer_requirement["user"]
            stats["next_user_class_message"] = message_requirement["user"]
            if stats["user_class"] == stats["previous_user_class"]:
                await message.channel.send(embed=demote_embed)
            stats["previous_user_class"] = "None"
            stats["next_user_class"] = user_class["user"]

        # "User" if buffer is between 10-25 GB and message count is >= 1000.
        elif buffer_requirement["user"] <= stats["buffer"] < buffer_requirement["power_user"] \
                and stats["message_count"] >= message_requirement["user"]:
            stats["user_class"] = user_class["user"]
            stats["next_user_class_buffer"] = buffer_requirement["power_user"]
            stats["next_user_class_message"] = message_requirement["power_user"]
            if stats["user_class"] == stats["next_user_class"]:
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await message.channel.send(embed=demote_embed)
            stats["previous_user_class"] = user_class["member"]
            stats["next_user_class"] = user_class["power_user"]

        # "Power User" if buffer is between 25-50 GB and message count is >= 2500.
        elif buffer_requirement["power_user"] <= stats["buffer"] < buffer_requirement["elite"] \
                and stats["message_count"] >= message_requirement["power_user"]:
            stats["user_class"] = user_class["power_user"]
            stats["next_user_class_buffer"] = buffer_requirement["elite"]
            stats["next_user_class_message"] = message_requirement["elite"]
            if stats["user_class"] == stats["next_user_class"]:
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await message.channel.send(embed=demote_embed)
            stats["previous_user_class"] = user_class["user"]
            stats["next_user_class"] = user_class["elite"]

        # "Elite" if buffer is between 50-100 GB and message count is >= 5000.
        elif buffer_requirement["elite"] <= stats["buffer"] < buffer_requirement["torrent_master"] \
                and stats["message_count"] >= message_requirement["elite"]:
            stats["user_class"] = user_class["elite"]
            stats["next_user_class_buffer"] = buffer_requirement["torrent_master"]
            stats["next_user_class_message"] = message_requirement["torrent_master"]
            if stats["user_class"] == stats["next_user_class"]:
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await message.channel.send(embed=demote_embed)
            stats["previous_user_class"] = user_class["power_user"]
            stats["next_user_class"] = user_class["torrent_master"]

        # "Torrent Master" if buffer is between 100-250 GB and message count is >= 10000.
        elif buffer_requirement["torrent_master"] < stats["buffer"] < buffer_requirement["power_tm"] \
                and stats["message_count"] >= message_requirement["torrent_master"]:
            stats["user_class"] = user_class["torrent_master"]
            stats["next_user_class_buffer"] = buffer_requirement["power_tm"]
            stats["next_user_class_message"] = message_requirement["power_tm"]
            if stats["user_class"] == stats["next_user_class"]:
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await message.channel.send(embed=demote_embed)
            stats["previous_user_class"] = user_class["elite"]
            stats["next_user_class"] = user_class["power_tm"]

        # "Power TM" if buffer is between 250-500 GB and message count is >= 22500.
        elif buffer_requirement["power_tm"] <= stats["buffer"] < buffer_requirement["elite_tm"] \
                and stats["message_count"] >= message_requirement["power_tm"]:
            stats["user_class"] = user_class["power_tm"]
            stats["next_user_class_buffer"] = buffer_requirement["elite_tm"]
            stats["next_user_class_message"] = message_requirement["elite_tm"]
            if stats["user_class"] == stats["next_user_class"]:
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await message.channel.send(embed=demote_embed)
            stats["previous_user_class"] = user_class["torrent_master"]
            stats["next_user_class"] = user_class["elite_tm"]

        # "Elite TM" if buffer is between 500-1024 GB and message count is >= 45000.
        elif buffer_requirement["elite_tm"] <= stats["buffer"] < buffer_requirement["legend"] \
                and stats["message_count"] >= message_requirement["elite_tm"]:
            stats["user_class"] = user_class["elite_tm"]
            stats["next_user_class_buffer"] = buffer_requirement["legend"]
            stats["next_user_class_message"] = message_requirement["legend"]
            if stats["user_class"] == stats["next_user_class"]:
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await message.channel.send(embed=demote_embed)
            stats["previous_user_class"] = user_class["power_tm"]
            stats["next_user_class"] = user_class["legend"]

        # "Legend" if buffer is > 1024 GB and message count is >= 80000.
        elif stats["buffer"] >= buffer_requirement["legend"] \
                and stats["message_count"] >= message_requirement["legend"]:
            stats["user_class"] = user_class["legend"]
            stats["next_user_class_buffer"] = 0
            stats["next_user_class_message"] = 0
            if stats["user_class"] == stats["next_user_class"]:
                await message.channel.send(embed=promote_embed)
            stats["previous_user_class"] = user_class["elite_tm"]
            stats["next_user_class"] = "None"

        # Return the dictionary.
        return stats

    @staticmethod
    async def calculate_buffer_remove(message: Message, stats):
        """ Remove the amount of buffer gained on message delete. Works exactly the same as calculate_buffer() but reversed. """

        # Get the number of words in a message.
        length = len(message.content.split())

        # Calculate the multiplier based on message length.
        if length in range(0, 3):
            multiplier = 0.33
        elif length in range(3, 5):
            multiplier = 0.67
        elif length in range(5, 8):
            multiplier = 0.9
        elif length in range(8, 11):
            multiplier = 1
        elif length in range(11, 16):
            multiplier = 1.1
        else:
            multiplier = 1.2

        # Calculate the baseline buffer.
        buffer = length * multiplier

        # 20% more buffer to be removed per message if the author is a server booster.
        role_server_booster = discord.utils.get(message.guild.roles, id=settings.get_value("role_server_booster"))
        is_booster = role_server_booster in message.author.roles
        if is_booster:
            buffer = buffer + buffer * 0.2

        # Set a maximum amount of buffer that will be removed.
        if buffer <= 40:
            stats["buffer"] -= buffer
        else:
            stats["buffer"] -= 40

        # Return the dictionary.
        return stats

    @staticmethod
    async def create_user():
        """ Initialize the JSON object for user stats if it doesn't exist yet. """
        # Dump the string into a JSON object and return it.
        stats_json = json.dumps(stats_template)
        return stats_json

    @staticmethod
    async def verify_integrity(stats):
        """ Verify the JSON object to make sure that it doesn't have missing keys. """

        # Iterate through the keys and values of the stats template.
        for key, value in stats_template.items():
            # If a key doesn't exist in the dictionary from parameter yet, add it.
            if key not in stats:
                stats[key] = value

        # Finally, return the new dictionary.
        return stats

    @staticmethod
    async def is_in_enabled_channels(message: Message) -> bool:
        """ Check if the sent message is from one of the enabled channels or not. """

        # Get all categories from the guild.
        categories = message.guild.categories

        # Ignore #shitposts channel.
        if message.channel.id == settings.get_value("channel_shitposts"):
            return False

        # Return true if the message was sent any channel under the community category.
        if any(message.channel.category.id == settings.get_value("category_community") for category in categories):
            return True

        # Return true if the message was sent in #mudae-lounge.
        if message.channel.id == settings.get_value("channel_mudae_lounge"):
            return True

        # TODO: Remove this on production. This is solely for testing convenience purpose.
        if message.channel.id == settings.get_value("channel_bot_testing"):
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


def setup(bot: Bot) -> None:
    """ Load the Leveling cog. """
    bot.add_cog(LevelingCog(bot))
    log.info("Commands loaded: leveling")
