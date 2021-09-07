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

user_class = {
    "member": "Member",
    "user": "User",
    "power_user": "Power User",
    "elite": "Elite",
    "torrent_master": "Torrent Master",
    "power_tm": "Power TM",
    "elite_tm": "Elite TM",
    "legend": "Legend",
}

buffer_req = {
    "member": 0,
    "user": 10240,
    "power_user": 25600,
    "elite": 51200,
    "torrent_master": 102400,
    "power_tm": 256000,
    "elite_tm": 512000,
    "legend": 1048576,
}

message_req = {
    "member": 0,
    "user": 1000,
    "power_user": 2500,
    "elite": 5000,
    "torrent_master": 10000,
    "power_tm": 22500,
    "elite_tm": 45000,
    "legend": 80000,
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
    "unique_promotion": 0,
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
        channel_enabled = await self.is_in_enabled_channels(message=message)
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
        channel_enabled = await self.is_in_enabled_channels(message=before)
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
        channel_enabled = await self.is_in_enabled_channels(message=message)
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
                role_custom = discord.utils.get(
                    member.guild.roles, id=stats["custom_role_id"]
                )
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

    async def calculate_buffer(self, message: Message, stats):
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
        role_server_booster = discord.utils.get(
            message.guild.roles, id=settings.get_value("role_server_booster")
        )
        if role_server_booster in message.author.roles:
            buffer += buffer * 0.2

        # Set a max cap to prevent abuse (low effort copy paste, trolling, copypasta, etc.)
        if buffer <= 40:
            stats["buffer"] += buffer
        else:
            stats["buffer"] += 40

        """ 
        On every message, attempt to compare their current user class with their previous and next user class to be promoted 
        or demoted to. If their current user class equals to the previous user class, it means that they just got demoted,
        and vice versa when promoted. Their previous, current, and next user class will be updated regardlessly. Note that for 
        "Member" class, we don't check for promotion because this is the lowest possible user class. The same applies to the 
        "Legend" class where demotion is not checked because it is the highest possible user class. "None" is a hidden user class
        that is made to not interact with anything and handle out of bound user classes for convenience.
        
        If the user is promoted to a new user class for the first time, give them a freeleech token. Unique promotion is kept track
        using an int ranging from 0-7 (8 user classes means that there will be 7 promotions). When it happens, add a reward field into
        the embed.
        
        Finally, assign the respective user class role to the member if they don't have one yet, while attempting to remove other 
        user class roles only if it exists (otherwise it would cause a "too many connections" issue).
        """

        # "Member" if buffer is between 0-10 GB and message count is >= 0.
        if (
            buffer_req["member"] <= stats["buffer"] < buffer_req["user"]
            and stats["message_count"] >= message_req["member"]
        ):
            stats["user_class"] = user_class["member"]
            stats["next_user_class_buffer"] = buffer_req["user"]
            stats["next_user_class_message"] = message_req["user"]
            if stats["user_class"] == stats["previous_user_class"]:
                await self.send_demote_embed(stats, message)
            stats["previous_user_class"] = "None"
            stats["next_user_class"] = user_class["user"]
            for key, value in user_class_role.items():
                role = discord.utils.get(message.guild.roles, id=value)
                if (
                    role not in message.author.roles
                    and role.id == user_class_role["member"]
                ):
                    await message.author.add_roles(role)
                elif (
                    role in message.author.roles
                    and role.id != user_class_role["member"]
                ):
                    await message.author.remove_roles(role)

        # "User" if buffer is between 10-25 GB and message count is >= 1000.
        elif (
            buffer_req["user"] <= stats["buffer"] < buffer_req["power_user"]
            and stats["message_count"] >= message_req["user"]
        ):
            stats["user_class"] = user_class["user"]
            stats["next_user_class_buffer"] = buffer_req["power_user"]
            stats["next_user_class_message"] = message_req["power_user"]
            if stats["user_class"] == stats["next_user_class"]:
                promote_embed = await self.create_promote_embed(stats, message)
                if stats["unique_promotion"] == 0:
                    stats["unique_promotion"] += 1
                    stats["freeleech_token"] += 1
                    promote_embed.add_field(
                        name="​", value="**Unique reward**: 1x Freeleech Token"
                    )
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await self.send_demote_embed(stats, message)
            stats["previous_user_class"] = user_class["member"]
            stats["next_user_class"] = user_class["power_user"]
            for key, value in user_class_role.items():
                role = discord.utils.get(message.guild.roles, id=value)
                if (
                    role not in message.author.roles
                    and role.id == user_class_role["user"]
                ):
                    await message.author.add_roles(role)
                elif (
                    role in message.author.roles and role.id != user_class_role["user"]
                ):
                    await message.author.remove_roles(role)

        # "Power User" if buffer is between 25-50 GB and message count is >= 2500.
        elif (
            buffer_req["power_user"] <= stats["buffer"] < buffer_req["elite"]
            and stats["message_count"] >= message_req["power_user"]
        ):
            stats["user_class"] = user_class["power_user"]
            stats["next_user_class_buffer"] = buffer_req["elite"]
            stats["next_user_class_message"] = message_req["elite"]
            if stats["user_class"] == stats["next_user_class"]:
                promote_embed = await self.create_promote_embed(stats, message)
                if stats["unique_promotion"] == 1:
                    stats["unique_promotion"] += 1
                    stats["freeleech_token"] += 1
                    promote_embed.add_field(
                        name="​", value="**Unique reward**: 1x Freeleech Token"
                    )
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await self.send_demote_embed(stats, message)
            stats["previous_user_class"] = user_class["user"]
            stats["next_user_class"] = user_class["elite"]
            for key, value in user_class_role.items():
                role = discord.utils.get(message.guild.roles, id=value)
                if (
                    role not in message.author.roles
                    and role.id == user_class_role["power_user"]
                ):
                    await message.author.add_roles(role)
                elif (
                    role in message.author.roles
                    and role.id != user_class_role["power_user"]
                ):
                    await message.author.remove_roles(role)

        # "Elite" if buffer is between 50-100 GB and message count is >= 5000.
        elif (
            buffer_req["elite"] <= stats["buffer"] < buffer_req["torrent_master"]
            and stats["message_count"] >= message_req["elite"]
        ):
            stats["user_class"] = user_class["elite"]
            stats["next_user_class_buffer"] = buffer_req["torrent_master"]
            stats["next_user_class_message"] = message_req["torrent_master"]
            if stats["user_class"] == stats["next_user_class"]:
                promote_embed = await self.create_promote_embed(stats, message)
                if stats["unique_promotion"] == 2:
                    stats["unique_promotion"] += 1
                    stats["freeleech_token"] += 2
                    promote_embed.add_field(
                        name="​", value="**Unique reward**: 2x Freeleech Token"
                    )
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await self.send_demote_embed(stats, message)
            stats["previous_user_class"] = user_class["power_user"]
            stats["next_user_class"] = user_class["torrent_master"]
            for key, value in user_class_role.items():
                role = discord.utils.get(message.guild.roles, id=value)
                if (
                    role not in message.author.roles
                    and role.id == user_class_role["elite"]
                ):
                    await message.author.add_roles(role)
                elif (
                    role in message.author.roles and role.id != user_class_role["elite"]
                ):
                    await message.author.remove_roles(role)

        # "Torrent Master" if buffer is between 100-250 GB and message count is >= 10000.
        elif (
            buffer_req["torrent_master"] <= stats["buffer"] < buffer_req["power_tm"]
            and stats["message_count"] >= message_req["torrent_master"]
        ):
            stats["user_class"] = user_class["torrent_master"]
            stats["next_user_class_buffer"] = buffer_req["power_tm"]
            stats["next_user_class_message"] = message_req["power_tm"]
            if stats["user_class"] == stats["next_user_class"]:
                promote_embed = await self.create_promote_embed(stats, message)
                if stats["unique_promotion"] == 3:
                    stats["unique_promotion"] += 1
                    stats["freeleech_token"] += 2
                    promote_embed.add_field(
                        name="​", value="**Unique reward**: 2x Freeleech Token"
                    )
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await self.send_demote_embed(stats, message)
            stats["previous_user_class"] = user_class["elite"]
            stats["next_user_class"] = user_class["power_tm"]
            for key, value in user_class_role.items():
                role = discord.utils.get(message.guild.roles, id=value)
                if (
                    role not in message.author.roles
                    and role.id == user_class_role["torrent_master"]
                ):
                    await message.author.add_roles(role)
                elif (
                    role in message.author.roles
                    and role.id != user_class_role["torrent_master"]
                ):
                    await message.author.remove_roles(role)

        # "Power TM" if buffer is between 250-500 GB and message count is >= 22500.
        elif (
            buffer_req["power_tm"] <= stats["buffer"] < buffer_req["elite_tm"]
            and stats["message_count"] >= message_req["power_tm"]
        ):
            stats["user_class"] = user_class["power_tm"]
            stats["next_user_class_buffer"] = buffer_req["elite_tm"]
            stats["next_user_class_message"] = message_req["elite_tm"]
            if stats["user_class"] == stats["next_user_class"]:
                promote_embed = await self.create_promote_embed(stats, message)
                if stats["unique_promotion"] == 4:
                    stats["unique_promotion"] += 1
                    stats["freeleech_token"] += 3
                    promote_embed.add_field(
                        name="​", value="**Unique reward**: 3x Freeleech Token"
                    )
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await self.send_demote_embed(stats, message)
            stats["previous_user_class"] = user_class["torrent_master"]
            stats["next_user_class"] = user_class["elite_tm"]
            for key, value in user_class_role.items():
                role = discord.utils.get(message.guild.roles, id=value)
                if (
                    role not in message.author.roles
                    and role.id == user_class_role["power_tm"]
                ):
                    await message.author.add_roles(role)
                elif (
                    role in message.author.roles
                    and role.id != user_class_role["power_tm"]
                ):
                    await message.author.remove_roles(role)

        # "Elite TM" if buffer is between 500-1024 GB and message count is >= 45000.
        elif (
            buffer_req["elite_tm"] <= stats["buffer"] < buffer_req["legend"]
            and stats["message_count"] >= message_req["elite_tm"]
        ):
            stats["user_class"] = user_class["elite_tm"]
            stats["next_user_class_buffer"] = buffer_req["legend"]
            stats["next_user_class_message"] = message_req["legend"]
            if stats["user_class"] == stats["next_user_class"]:
                promote_embed = await self.create_promote_embed(stats, message)
                if stats["unique_promotion"] == 5:
                    stats["unique_promotion"] += 1
                    stats["freeleech_token"] += 3
                    promote_embed.add_field(
                        name="​", value="**Unique reward**: 3x Freeleech Token"
                    )
                await message.channel.send(embed=promote_embed)
            elif stats["user_class"] == stats["previous_user_class"]:
                await self.send_demote_embed(stats, message)
            stats["previous_user_class"] = user_class["power_tm"]
            stats["next_user_class"] = user_class["legend"]
            for key, value in user_class_role.items():
                role = discord.utils.get(message.guild.roles, id=value)
                if (
                    role not in message.author.roles
                    and role.id == user_class_role["elite_tm"]
                ):
                    await message.author.add_roles(role)
                elif (
                    role in message.author.roles
                    and role.id != user_class_role["elite_tm"]
                ):
                    await message.author.remove_roles(role)

        # "Legend" if buffer is > 1024 GB and message count is >= 80000.
        elif (
            stats["buffer"] >= buffer_req["legend"]
            and stats["message_count"] >= message_req["legend"]
        ):
            stats["user_class"] = user_class["legend"]
            stats["next_user_class_buffer"] = 0
            stats["next_user_class_message"] = 0
            if stats["user_class"] == stats["next_user_class"]:
                promote_embed = await self.create_promote_embed(stats, message)
                if stats["unique_promotion"] == 6:
                    stats["unique_promotion"] += 1
                    stats["freeleech_token"] += 5
                    promote_embed.add_field(
                        name="​", value="**Unique reward**: 5x Freeleech Token"
                    )
                await message.channel.send(embed=promote_embed)
            stats["previous_user_class"] = user_class["elite_tm"]
            stats["next_user_class"] = "None"
            for key, value in user_class_role.items():
                role = discord.utils.get(message.guild.roles, id=value)
                if (
                    role not in message.author.roles
                    and role.id == user_class_role["legend"]
                ):
                    await message.author.add_roles(role)
                elif (
                    role in message.author.roles
                    and role.id != user_class_role["legend"]
                ):
                    await message.author.remove_roles(role)

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
        role_server_booster = discord.utils.get(
            message.guild.roles, id=settings.get_value("role_server_booster")
        )
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
        """Verify the JSON object to make sure that it doesn't have missing keys or contains keys that shouldn't exist."""

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
            message.channel.category.id == settings.get_value("category_community")
            for _ in message.guild.categories
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

    @staticmethod
    async def create_promote_embed(stats, message):
        # Make an embed to be sent on user promotion and let them know that they were rewarded a FL token.
        promote_embed = embeds.make_embed(
            title="Promoted!",
            description=f"{message.author.mention} has been promoted to {stats['next_user_class']}!",
            thumbnail_url=message.author.avatar_url,
            color="green",
        )
        return promote_embed

    @staticmethod
    async def send_demote_embed(stats, message):
        # Make an embed to be sent on user demotion.
        demote_embed = embeds.make_embed(
            title="Demoted!",
            description=f"{message.author.mention} has been demoted to {stats['previous_user_class']}!",
            thumbnail_url=message.author.avatar_url,
            color="red",
        )
        await message.channel.send(embed=demote_embed)


def setup(bot: Bot) -> None:
    """Load the Leveling cog."""
    bot.add_cog(LevelingCog(bot))
    log.info("Commands loaded: leveling")
