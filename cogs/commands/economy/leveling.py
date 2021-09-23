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
    "member": {
        "user_class": "Member",
        "previous_user_class": (),
        "next_user_class": (
            "User",
            "Power User",
            "Elite",
            "Torrent Master",
            "Power TM",
            "Elite TM",
            "Legend",
        ),
        "role": settings.get_value("role_member"),
        "buffer_requirement": 0,
        "message_requirement": 0,
        "next_buffer_requirement": 10240,
        "next_message_requirement": 1000,
        "token_reward": 0,
    },
    "user": {
        "user_class": "User",
        "previous_user_class": ("Member",),
        "next_user_class": (
            "Power User",
            "Elite",
            "Torrent Master",
            "Power TM",
            "Elite TM",
            "Legend",
        ),
        "role": settings.get_value("role_user"),
        "buffer_requirement": 10240,
        "message_requirement": 1000,
        "next_buffer_requirement": 25600,
        "next_message_requirement": 2500,
        "token_reward": 1,
    },
    "power_user": {
        "user_class": "Power User",
        "previous_user_class": ("Member", "User"),
        "next_user_class": (
            "Elite",
            "Torrent Master",
            "Power TM",
            "Elite TM",
            "Legend",
        ),
        "role": settings.get_value("role_power_user"),
        "buffer_requirement": 25600,
        "message_requirement": 2500,
        "next_buffer_requirement": 51200,
        "next_message_requirement": 5000,
        "token_reward": 1,
    },
    "elite": {
        "user_class": "Elite",
        "previous_user_class": ("Member", "User", "Power User"),
        "next_user_class": ("Torrent Master", "Power TM", "Elite TM", "Legend"),
        "role": settings.get_value("role_elite"),
        "buffer_requirement": 51200,
        "message_requirement": 5000,
        "next_buffer_requirement": 102400,
        "next_message_requirement": 10000,
        "token_reward": 2,
    },
    "torrent_master": {
        "user_class": "Torrent Master",
        "previous_user_class": ("Member", "User", "Power User", "Elite"),
        "next_user_class": ("Power TM", "Elite TM", "Legend"),
        "role": settings.get_value("role_torrent_master"),
        "buffer_requirement": 102400,
        "message_requirement": 10000,
        "next_buffer_requirement": 256000,
        "next_message_requirement": 22500,
        "token_reward": 2,
    },
    "power_tm": {
        "user_class": "Power TM",
        "previous_user_class": (
            "Member",
            "User",
            "Power User",
            "Elite",
            "Torrent Master",
        ),
        "next_user_class": ("Elite TM", "Legend"),
        "role": settings.get_value("role_power_tm"),
        "buffer_requirement": 256000,
        "message_requirement": 22500,
        "next_buffer_requirement": 512000,
        "next_message_requirement": 45000,
        "token_reward": 3,
    },
    "elite_tm": {
        "user_class": "Elite TM",
        "previous_user_class": (
            "Member",
            "User",
            "Power User",
            "Elite",
            "Torrent Master",
            "Power TM",
        ),
        "next_user_class": ("Legend",),
        "role": settings.get_value("role_elite_tm"),
        "buffer_requirement": 512000,
        "message_requirement": 45000,
        "next_buffer_requirement": 1048576,
        "next_message_requirement": 80000,
        "token_reward": 3,
    },
    "legend": {
        "user_class": "Legend",
        "previous_user_class": (
            "Member",
            "User",
            "Power User",
            "Elite",
            "Torrent Master",
            "Power TM",
            "Elite TM",
        ),
        "next_user_class": (),
        "role": settings.get_value("role_legend"),
        "buffer_requirement": 1048576,
        "message_requirement": 80000,
        "next_buffer_requirement": 0,
        "next_message_requirement": 0,
        "token_reward": 5,
    },
}

user_class_role = {
    "member": settings.get_value("role_member"),
    "user": settings.get_value("role_user"),
    "power_user": settings.get_value("role_power_user"),
    "elite": settings.get_value("role_elite"),
    "torrent_master": settings.get_value("role_torrent_master"),
    "power_tm": settings.get_value("role_power_tm"),
    "elite_tm": settings.get_value("role_elite_tm"),
    "legend": settings.get_value("role_legend"),
}

# The user stats template.
stats_template = {
    "user_class": "Member",
    "previous_user_class": (),
    "next_user_class": (
        "User",
        "Power User",
        "Elite",
        "Torrent Master",
        "Power TM",
        "Elite TM",
        "Legend",
    ),
    "buffer": 0,
    "next_user_class_buffer": 0,
    "message_count": 0,
    "next_user_class_message": 0,
    "unique_promotion": [],
    "freeleech_token": 0,
    "vouch": 0,
    "has_custom_role": False,
    "custom_role_id": 0,
    "daily_upgrade": 0,
    "hue_upgrade": [],
    "saturation_upgrade": 0,
    "value_upgrade": 0,
    "daily_timestamp": 0,
    "achievements": [],
}


class LevelingCog(Cog):
    """Leveling cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        """The entry point for buffer calculation and promotion/demotion on every messages sent."""

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

        # Calculate buffer gain and increment the message count in allowed channels.
        channel_enabled = await self.is_in_enabled_channels(message)
        if channel_enabled:
            stats["message_count"] += 1
            stats = await self.calculate_buffer(message, stats)
            # Dump the modified JSON into the db.
            stats_json = json.dumps(stats)
            achievements.update(dict(id=user["id"], stats=stats_json), ["id"])
            db.commit()

        # Close the connection.
        db.close()

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Change the earned buffer on message edit."""

        # If the author is a bot, skip them.
        if before.author.bot:
            return

        # Connect to the database and get the achievement table.
        db = dataset.connect(database.get_db())
        achievements = db["achievements"]
        user = achievements.find_one(user_id=before.author.id)

        # If the user is not found, initialize their entry, insert it into the db and get their entry which was previously a NoneType.
        if not user:
            stats_json = await self.create_user()
            achievements.insert(dict(user_id=before.author.id, stats=stats_json))
            user = achievements.find_one(user_id=before.author.id)

        # Load the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user["stats"])

        # Recalculate buffer gain only in allowed channels.
        channel_enabled = await self.is_in_enabled_channels(before)
        if channel_enabled:
            # Remove the buffer gained from the message pre-edit.
            stats_old = await self.calculate_buffer_remove(before, stats)
            # Calculate the buffer gained from the newly edited message.
            stats_new = await self.calculate_buffer(after, stats_old)
            # Dump the modified JSON into the db.
            stats_json = json.dumps(stats_new)
            achievements.update(dict(id=user["id"], stats=stats_json), ["id"])
            db.commit()

        # Close the connection.
        db.close()

    @commands.Cog.listener()
    async def on_message_delete(self, message: Message):
        """Remove the earned buffer on message delete."""

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

        # Revert the buffer gain and message count in allowed channels.
        channel_enabled = await self.is_in_enabled_channels(message)
        if channel_enabled:
            stats["message_count"] -= 1
            stats = await self.calculate_buffer_remove(message, stats)
            # Dump the modified JSON into the db.
            stats_json = json.dumps(stats)
            achievements.update(dict(id=user["id"], stats=stats_json), ["id"])
            db.commit()

        # Close the connection.
        db.close()

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        """Automatically add the user's custom role back if possible."""
        # Open a connection to the database.
        db = dataset.connect(database.get_db())

        # Get the user that just joined.
        achievements = db["achievements"]
        user = achievements.find_one(user_id=member.id)

        # If the user is found, load the JSON object in the database into a dictionary.
        if user:
            stats = json.loads(user["stats"])
            # Get their custom role.
            if stats["has_custom_role"]:
                role_custom = discord.utils.get(member.guild.roles, id=stats["custom_role_id"])
                # If the role is found, add it back to the user. Otherwise, reset their custom role stats.
                if role_custom:
                    await member.add_roles(role_custom)
                else:
                    stats["has_custom_role"] = False
                    stats["custom_role_id"] = 0
                    # Dump the modified JSON into the db.
                    stats_json = json.dumps(stats)
                    achievements.update(dict(id=user["id"], stats=stats_json), ["id"])
                    db.commit()

        # Close the connection.
        db.close()

    @staticmethod
    async def calculate_buffer(message: Message, stats):
        """Calculate the amount of buffer gained from messages and promote/demote conditionally."""

        # Get the number of words in a message.
        length = len(message.content.split())

        # Heavily punishes emote spams, links, gifs, etc.
        if length in range(0, 2):
            multiplier = 0.33
        # Discourage very short messages.
        elif length in range(2, 4):
            multiplier = 0.67
        # Slightly punish short messages.
        elif length in range(4, 6):
            multiplier = 0.9
        # Normal multiplier to average messages.
        elif length in range(6, 11):
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
        if role_server_booster in message.author.roles:
            buffer += buffer * 0.2

        # Set a max cap to prevent abuse (low effort copy paste, trolling, copypasta, etc.)
        if buffer <= 40:
            stats["buffer"] += buffer
        else:
            stats["buffer"] += 40

        # Update the user class, buffer and message requirement according to their user class.
        for key, value in user_class.items():
            if (
                stats["buffer"] >= value["buffer_requirement"]
                and stats["message_count"] >= value["message_requirement"]
            ):
                stats["user_class"] = value["user_class"]
                stats["next_user_class_buffer"] = value["next_buffer_requirement"]
                stats["next_user_class_message"] = value["next_message_requirement"]
                # Set a variable to temporarily save the previous and next user classes value of the user meant to be updated.
                previous_user_class = value["previous_user_class"]
                next_user_class = value["next_user_class"]

        # If the current user class matches one of the classes in their next user classes, it means that they just got promoted.
        if stats["user_class"] in stats["next_user_class"]:
            # Prepare the promote embed.
            embed = embeds.make_embed(
                title="Promoted!",
                description=f"{message.author.mention} has been promoted to {stats['user_class']}!",
                thumbnail_url=message.author.avatar_url,
                color="green",
            )
            # Check to see if the promotion is the first time.
            if stats["user_class"] not in stats["unique_promotion"]:
                # Append to the unique_promotion array to mark this unique promotion event as happened.
                stats["unique_promotion"].append(stats["user_class"])
                # Loop through the user_class dict to get the respective amount of FL token to be received.
                for key, value in user_class.items():
                    if stats["user_class"] == value["user_class"]:
                        stats["freeleech_token"] += value["token_reward"]
                        # Add an embed field to let the user know that they received a reward.
                        embed.add_field(
                            name="​",
                            value=f"**Unique reward:**: "
                            f"{value['token_reward']}x Freeleech {'Tokens' if value['token_reward'] > 1 else 'Token'}",
                        )
            # Finally, send the embed.
            await message.channel.send(embed=embed)

        # If the current user class matches one of the classes in their previous user classes, it means that they just got demoted.
        if stats["user_class"] in stats["previous_user_class"]:
            # Prepare the demote embed.
            embed = embeds.make_embed(
                title="Demoted!",
                description=f"{message.author.mention} has been demoted to {stats['user_class']}!",
                thumbnail_url=message.author.avatar_url,
                color="red",
            )
            # Send the embed.
            await message.channel.send(embed=embed)

        # Update the user's previous and next user classes value after the promotion/demotion check is finished. If this is done above,
        # the stats will be updated before the checks and fail to work the user class overlaps doesn't happen for it to compare.
        stats["previous_user_class"] = previous_user_class
        stats["next_user_class"] = next_user_class

        # Assign the respective class role if the user don't have one yet, while attempting to remove other class roles if exist.
        for key, value in user_class_role.items():
            role = discord.utils.get(message.guild.roles, id=value)
            if role in message.author.roles and role.name != stats["user_class"]:
                await message.author.remove_roles(role)
            elif role not in message.author.roles and role.name == stats["user_class"]:
                await message.author.add_roles(role)

        # Return the dictionary.
        return stats

    @staticmethod
    async def calculate_buffer_remove(message: Message, stats):
        """Remove the amount of buffer gained on message delete. Works exactly the same as calculate_buffer() but reversed."""

        # Get the number of words in a message.
        length = len(message.content.split())

        # Calculate the multiplier based on message length.
        if length in range(0, 2):
            multiplier = 0.33
        elif length in range(2, 4):
            multiplier = 0.67
        elif length in range(4, 6):
            multiplier = 0.9
        elif length in range(6, 11):
            multiplier = 1
        elif length in range(11, 16):
            multiplier = 1.1
        else:
            multiplier = 1.2

        # Calculate the baseline buffer.
        buffer = length * multiplier

        # 20% more buffer to be removed per message if the author is a server booster.
        role_server_booster = discord.utils.get(message.guild.roles, id=settings.get_value("role_server_booster"))
        if role_server_booster in message.author.roles:
            buffer += buffer * 0.2

        # Set a maximum amount of buffer that will be removed.
        if buffer <= 40:
            stats["buffer"] -= buffer
        else:
            stats["buffer"] -= 40

        # Return the dictionary.
        return stats

    @staticmethod
    async def create_user():
        """Initialize the JSON object for user stats if it doesn't exist yet."""
        # Dump the string into a JSON object and return it.
        stats_json = json.dumps(stats_template)
        return stats_json

    @staticmethod
    async def verify_integrity(stats):
        """Verify the JSON object to make sure that it doesn't have missing keys or contains keys that shouldn't exist. If major data
         structure or type are changed in the stats JSON, write some single-use code here and applies to the entire database with
        /refresh command. MAKE SURE TO SAVE A COPY OF THE DATABASE FIRST BEFORE DOING SO."""

        # Iterate through the keys and values of the stats template.
        for key, value in stats_template.items():
            # If a key doesn't exist in the dictionary from parameter yet, add it.
            if key not in stats:
                stats[key] = value

        # Iterate through the stats template and remove any bloated keys in the user's stats JSON. copy() is used to create a
        # mirrored version of the stats because changing the dictionary size with .pop() while iterating will raise RuntimeError.
        for key in stats.copy():
            if key not in stats_template:
                stats.pop(key)

        # Finally, return the new dictionary.
        return stats

    @staticmethod
    async def is_in_enabled_channels(message: Message) -> bool:
        """Check if the sent message is from one of the enabled channels or not."""

        """
        Check for excepted channels first before iterating through the categories for better efficiency. If-elif is used 
        in favor of multiple if statements for better efficiency.
        """
        # Return False if the channel is #shitposts.
        if message.channel.id == settings.get_value("channel_shitposts"):
            return False
        # Return True if the channel is #mudae-lounge or #bot-testing (for testing convenience).
        elif message.channel.id in {
            settings.get_value("channel_mudae_lounge"),
            settings.get_value("channel_bot_testing"),
        }:
            return True
        # Return True if the channel is under the "Community" category.
        elif any(
            message.channel.category.id == settings.get_value("category_community") for _ in message.guild.categories
        ):
            return True
        # Return False otherwise.
        else:
            return False

    @staticmethod
    async def get_buffer_string(buffer) -> str:
        """Display the buffer in a beautified format of MB, GB, and TB."""

        """If buffer >= 1024 GB, display it in TB. If >= 1024 MB, display it in GB. Otherwise, display it in MB."""
        if buffer >= 1024 ** 2:
            buffer_string = f"{round(buffer / (1024 ** 2), 2)} TB"
        elif buffer >= 1024:
            buffer_string = f"{round(buffer / 1024, 2)} GB"
        else:
            buffer_string = f"{round(buffer, 2)} MB"

        # Return the formatted string.
        return buffer_string


def setup(bot: Bot) -> None:
    """Load the Leveling cog."""
    bot.add_cog(LevelingCog(bot))
    log.info("Commands loaded: leveling")
