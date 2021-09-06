import datetime
import json
import logging
import re

import dataset
import discord
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from cogs.commands import settings
from utils import embeds, database
from utils.record import record_usage

log = logging.getLogger(__name__)


class Console(Cog):
    """Developer console cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="system",
        name="call",
        description="Single target cheat commands",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="user",
                description="The user's stats to be modified",
                option_type=6,
                required=True,
            ),
            create_option(
                name="set_buffer",
                description="Set the buffer value of a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="remove_buffer",
                description="Remove some buffer from a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="add_buffer",
                description="Add some buffer to a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="set_message_count",
                description="Set the message count value of a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="set_unique_promotion",
                description="Set the number of unique promotions of a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="set_freeleech_token",
                description="Set the FL token value of a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="set_vouch",
                description="Set the vouch value of a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="has_custom_role",
                description="Set the custom role boolean value of a user",
                option_type=5,
                required=False,
            ),
            create_option(
                name="custom_role_id",
                description="Set the custom role ID of a user",
                option_type=3,
                required=False,
            ),
            create_option(
                name="set_daily_upgrade",
                description="Set the daily upgrade value of a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="set_hue_upgrade",
                description="Set the hue upgrade value of a user",
                option_type=3,
                required=False,
            ),
            create_option(
                name="set_saturation_upgrade",
                description="Set the saturation upgrade value of a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="set_brightness_upgrade",
                description="Set the brightness upgrade value of a user",
                option_type=4,
                required=False,
            ),
            create_option(
                name="set_daily_timestamp",
                description="Set the daily timestamp (Unix) value of a user",
                option_type=4,
                required=False,
            ),
        ],
        base_default_permission=False,
        base_permissions={
            settings.get_value("guild_id"): [
                create_permission(
                    settings.get_value("role_staff"),
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
                create_permission(
                    settings.get_value("role_trial_mod"),
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
            ]
        },
    )
    async def console(
        self,
        ctx: SlashContext,
        user: discord.User,
        set_buffer: int = None,
        remove_buffer: int = None,
        add_buffer: int = None,
        set_message_count: int = None,
        set_unique_promotion: int = None,
        set_freeleech_token: int = None,
        set_vouch: int = None,
        has_custom_role: bool = None,
        custom_role_id: str = None,
        set_daily_upgrade: str = None,
        set_hue_upgrade: str = None,
        set_saturation_upgrade: int = None,
        set_brightness_upgrade: int = None,
        set_daily_timestamp: int = None,
    ):
        """Single target cheat commands."""
        await ctx.defer()

        # Connect to the database and get the achievement table.
        db = dataset.connect(database.get_db())
        achievements = db["achievements"]

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        # Attempt to find the user who issued the command.
        user_entry = achievements.find_one(user_id=user.id)

        # Return if the user is not found in the database.
        if not user_entry:
            await embeds.error_message(
                ctx=ctx, description="Could not find the specified user."
            )
            db.close()
            return

        # Loads the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user_entry["stats"])

        # Initialize the embed.
        embed = embeds.make_embed(color="green")

        # Set the buffer to a specific target value. Must be >= 0.
        if set_buffer is not None and set_buffer >= 0:
            stats["buffer"] = set_buffer
            embed.description = f"{user.mention}'s buffer has been set to {set_buffer}!"
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is < 0, return.
        elif set_buffer is not None:
            await embeds.error_message(
                ctx=ctx, description="Buffer value must be equal or greater than 0."
            )
            db.close()
            return

        # Remove an amount of buffer from the user. The amount to be reduced and the total amount must be >= 0.
        if (
            remove_buffer is not None
            and remove_buffer >= 0
            and stats["buffer"] - remove_buffer >= 0
        ):
            stats["buffer"] -= remove_buffer
            embed.description = (
                f"{user.mention}'s buffer has been decreased by {remove_buffer}!"
            )
            await ctx.send(embed=embed)
        # Else if the input parameter exists but it or the total amount is < 0, return.
        elif remove_buffer is not None:
            await embeds.error_message(
                ctx=ctx,
                description="The amount of buffer to be removed or the total amount must be equal or greater than 0.",
            )
            db.close()
            return

        # Add an amount of buffer to the user. Must be >= 0.
        if add_buffer is not None and add_buffer >= 0:
            stats["buffer"] += add_buffer
            embed.description = (
                f"{user.mention}'s buffer has been increased by {add_buffer}!"
            )
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is < 0, return.
        elif add_buffer is not None:
            await embeds.error_message(
                ctx=ctx,
                description="Buffer addition value must be equal or greater than 0.",
            )
            db.close()
            return

        # Set the message count of a user. Must be >= 0.
        if set_message_count is not None and set_message_count >= 0:
            stats["message_count"] = set_message_count
            embed.description = (
                f"{user.mention}'s upload value has been set to {set_message_count}!"
            )
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is < 0, return.
        elif set_message_count is not None:
            await embeds.error_message(
                ctx=ctx,
                description="Message count value must be equal or greater than 0.",
            )
            db.close()
            return

        # Set the number of unique promotions of a user. Must be from 0-7.
        if set_unique_promotion is not None and set_unique_promotion in range(0, 8):
            stats["unique_promotion"] = set_unique_promotion
            embed.description = f"{user.mention}'s unique promotion count has been set to {set_unique_promotion}!"
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is not between 0-7, return.
        elif set_unique_promotion is not None:
            await embeds.error_message(
                ctx=ctx, description="Unique promotion count must be between 0 to 7."
            )
            db.close()
            return

        # Set the FL token of a user. Must be >= 0.
        if set_freeleech_token is not None and set_freeleech_token >= 0:
            stats["freeleech_token"] = set_freeleech_token
            embed.description = f"{user.mention}'s freeleech token value has been set to {set_freeleech_token}!"
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is < 0, return.
        elif set_freeleech_token is not None:
            await embeds.error_message(
                ctx=ctx,
                description="Freeleech token value must be equal or greater than 0.",
            )
            db.close()
            return

        # Set the vouch count of a user. Must be >= 0.
        if set_vouch is not None and set_vouch >= 0:
            stats["vouch"] = set_vouch
            embed.description = (
                f"{user.mention}'s vouch value has been set to {set_vouch}!"
            )
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is < 0, return.
        elif set_vouch is not None:
            await embeds.error_message(
                ctx=ctx, description="Vouch value must be equal or greater than 0."
            )
            db.close()
            return

        # Set the custom role boolean flag of a user.
        if has_custom_role is not None:
            stats["has_custom_role"] = has_custom_role
            embed.description = f"{user.mention}'s custom role flag value has been set to {has_custom_role}!"
            await ctx.send(embed=embed)

        # Prevent misuse by assigning people one of those role IDs from "Staff" or above and kick them
        # to give them that role automatically after rejoining the server.
        staff_roles = [
            "794473938373705758",
            "793756169687662642",
            "794080306311331840",
            "728677807856680971",
            "870228470796550205",
            "763031634379276308",
        ]
        # Must be a digit and must not be any of the roles above "Staff".
        if (
            custom_role_id
            and custom_role_id.isdigit()
            and not any(custom_role_id == staff_role for staff_role in staff_roles)
        ):
            # Convert the string to int. String type was used because Slash command sucks ass and didn't have bigint data type.
            stats["custom_role_id"] = int(custom_role_id)
            embed.description = f"{user.mention}'s custom role ID value has been set to {custom_role_id}!"
            await ctx.send(embed=embed)
        # Else if the input parameter exists...
        elif custom_role_id:
            # ...but is not a digit.
            if not custom_role_id.isdigit():
                await embeds.error_message(
                    ctx=ctx, description="Role ID value must be a non-negative digit."
                )
            # ...but is one of the roles from "Staff" or higher.
            if any(custom_role_id == staff_role for staff_role in staff_roles):
                await embeds.error_message(
                    ctx=ctx, description="This role ID value is not assignable."
                )
            db.close()
            return

        # Set the daily upgrade value of a user. Must be between 0-100.
        if set_daily_upgrade is not None and set_daily_upgrade in range(0, 101):
            stats["daily_upgrade"] = set_daily_upgrade
            embed.description = f"{user.mention}'s daily upgrade value has been set to {set_daily_upgrade}!"
            await ctx.send(embed=embed)
            # Else if the input parameter exists but is not between 0-100, return.
        elif set_daily_upgrade is not None:
            await embeds.error_message(
                ctx=ctx, description="Daily upgrade value must be between 0 and 100."
            )
            db.close()
            return

        # Set the hue upgrade value of a user by using a Regex to capture only valid options.
        if set_hue_upgrade:
            match_list = re.findall(
                "(red|green|yellow|blue|magenta|cyan)", set_hue_upgrade
            )
            # If there is at least one item in the match list, set the value.
            if match_list:
                stats["hue_upgrade"] = match_list
                embed.description = (
                    f"{user.mention}'s hue upgrade value has been set to {match_list}!"
                )
                await ctx.send(embed=embed)
            # Attempt to check if the input value is "none". If it does, give the user an empty list to remove their upgrades.
            elif set_hue_upgrade.lower() == "none":
                stats["hue_upgrade"] = []
                embed.description = (
                    f"{user.mention}'s hue upgrade value has been emptied!"
                )
                await ctx.send(embed=embed)
            # Otherwise if the match list is empty, return.
            else:
                color_options = ["red", "yellow", "green", "cyan", "blue", "magenta"]
                await embeds.error_message(
                    ctx=ctx,
                    description=f"Color must be one or more of the following options: {', '.join(option for option in color_options)}"
                    f", or set the input value to 'none' to remove the upgrades.",
                )
                db.close()
                return

        # Set the saturation upgrade value of a user. Must be between 0-100.
        if set_saturation_upgrade is not None and set_saturation_upgrade in range(
            0, 101
        ):
            stats["saturation_upgrade"] = set_saturation_upgrade
            embed.description = f"{user.mention}'s saturation upgrade value has been set to {set_saturation_upgrade}!"
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is not between 0-100, return.
        elif set_saturation_upgrade is not None:
            await embeds.error_message(
                ctx=ctx,
                description="Saturation upgrade value must be between 0 and 100.",
            )
            db.close()
            return

        # Set the brightness upgrade value of a user. Must be between 0-100.
        if set_brightness_upgrade is not None and set_brightness_upgrade in range(
            0, 101
        ):
            stats["value_upgrade"] = set_brightness_upgrade
            embed.description = f"{user.mention}'s brightness upgrade value has been set to {set_brightness_upgrade}!"
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is not between 0-100, return.
        elif set_brightness_upgrade is not None:
            await embeds.error_message(
                ctx=ctx,
                description="Brightness upgrade value must be between 0 and 100.",
            )
            db.close()
            return

        # Set the daily timestamp of a user (Unix format). Must be >= 0.
        if set_daily_timestamp is not None and set_daily_timestamp >= 0:
            stats["daily_timestamp"] = set_daily_timestamp
            time = datetime.datetime.fromtimestamp(set_daily_timestamp)
            embed.description = (
                f"{user.mention}'s daily timestamp value has been set to {time}!"
            )
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is < 0, return.
        elif set_daily_timestamp is not None:
            await embeds.error_message(
                ctx=ctx, description="Daily timestamp value must be greater than 0."
            )
            db.close()
            return

        # Dump the modified JSON into the db and close it.
        stats_json = json.dumps(stats)
        achievements.update(dict(id=user_entry["id"], stats=stats_json), ["id"])

        # Commit the changes to the database and close it.
        db.commit()
        db.close()

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="system",
        name="global",
        description="Global cheat commands",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="add_buffer",
                description="Add some buffer to all users",
                option_type=4,
                required=False,
            ),
            create_option(
                name="remove_buffer",
                description="Remove some buffer from all users",
                option_type=4,
                required=False,
            ),
            create_option(
                name="add_freeleech_token",
                description="Add some FL tokens to all users",
                option_type=4,
                required=False,
            ),
            create_option(
                name="remove_freeleech_token",
                description="Remove some FL tokens from all users",
                option_type=4,
                required=False,
            ),
        ],
        base_default_permission=False,
        base_permissions={
            settings.get_value("guild_id"): [
                create_permission(
                    settings.get_value("role_staff"),
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
                create_permission(
                    settings.get_value("role_trial_mod"),
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
            ]
        },
    )
    async def global_console(
        self,
        ctx: SlashContext,
        add_buffer: int = None,
        remove_buffer: int = None,
        add_freeleech_token: int = None,
        remove_freeleech_token: int = None,
    ):
        """ " Global commands."""
        await ctx.defer()

        # Connect to the database and get the achievement table.
        db = dataset.connect(database.get_db())
        achievements = db["achievements"]

        # Initialize the embed.
        embed = embeds.make_embed(color="green")

        # Add an amount of buffer to all users. Must be >= 0.
        if add_buffer is not None and add_buffer >= 0:
            entry_counter = 0
            # Iterate through all user entries in the database and update them.
            for entry in achievements:
                entry_counter += 1
                entry_stats = json.loads(entry["stats"])
                entry_stats["buffer"] += add_buffer
                entry_stats_json = json.dumps(entry_stats)
                achievements.update(
                    dict(id=entry["id"], stats=entry_stats_json), ["id"]
                )
            embed.description = (
                f"{entry_counter} members buffer have been increased by {add_buffer}!"
            )
            await ctx.send(embed=embed)
            # Else if the input parameter exists but is < 0, return.
        elif add_buffer is not None:
            await embeds.error_message(
                ctx=ctx,
                description="Global buffer addition value must be equal or greater than 0.",
            )
            db.close()
            return

        # Remove an amount of buffer to all users. Must be >= 0. This is to revert any whoopsies from global add buffer command.
        if remove_buffer is not None and remove_buffer >= 0:
            entry_counter = 0
            # Iterate through all user entries in the database and update them.
            for entry in achievements:
                entry_counter += 1
                entry_stats = json.loads(entry["stats"])
                # If the total amount would go below 0, set it to 0 instead.
                entry_stats["buffer"] -= (
                    remove_buffer if entry_stats["buffer"] - remove_buffer >= 0 else 0
                )
                # Dump the modified JSON into the db.
                entry_stats_json = json.dumps(entry_stats)
                achievements.update(
                    dict(id=entry["id"], stats=entry_stats_json), ["id"]
                )
            embed.description = f"{entry_counter} members buffer have been decreased by {remove_buffer}!"
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is < 0, return.
        elif remove_buffer is not None:
            await embeds.error_message(
                ctx=ctx,
                description="Global buffer addition value must be equal or greater than 0.",
            )
            db.close()
            return

        # Add an amount of FL token to all users. Must be >= 0.
        if add_freeleech_token is not None and add_freeleech_token >= 0:
            entry_counter = 0
            # Iterate through all user entries in the database and update them.
            for entry in achievements:
                entry_counter += 1
                entry_stats = json.loads(entry["stats"])
                entry_stats["freeleech_token"] += add_freeleech_token
                entry_stats_json = json.dumps(entry_stats)
                achievements.update(
                    dict(id=entry["id"], stats=entry_stats_json), ["id"]
                )
            embed.description = f"{add_freeleech_token} freeleech token(s) were given to {entry_counter} members!"
            await ctx.send(embed=embed)
            # Else if the input parameter exists but is < 0, return.
        elif add_freeleech_token is not None:
            await embeds.error_message(
                ctx=ctx,
                description="Global FL token addition value must be equal or greater than 0.",
            )
            db.close()
            return

        # Remove an amount of buffer to all users. Must be >= 0. This is to revert any whoopsies from global add buffer command.
        if remove_freeleech_token is not None and remove_freeleech_token >= 0:
            entry_counter = 0
            # Iterate through all user entries in the database and update them.
            for entry in achievements:
                entry_counter += 1
                entry_stats = json.loads(entry["stats"])
                # If the total amount would go below 0, set it to 0 instead.
                entry_stats["freeleech_token"] -= (
                    remove_freeleech_token
                    if entry_stats["freeleech_token"] - remove_freeleech_token < 0
                    else 0
                )
                # Dump the modified JSON into the db.
                entry_stats_json = json.dumps(entry_stats)
                achievements.update(
                    dict(id=entry["id"], stats=entry_stats_json), ["id"]
                )
            embed.description = f"{remove_freeleech_token} freeleech token(s) were removed from {entry_counter} members!"
            await ctx.send(embed=embed)
        # Else if the input parameter exists but is < 0, return.
        elif remove_freeleech_token is not None:
            await embeds.error_message(
                ctx=ctx,
                description="Global buffer reduction value must be equal or greater than 0.",
            )
            db.close()
            return

        # Commit the changes to the database and close it.
        db.commit()
        db.close()

    @commands.bot_has_permissions(send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="refresh",
        description="Reload the user profile stats.",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="user",
                description="The user's stats to be reloaded.",
                option_type=6,
                required=False,
            ),
        ],
        default_permission=False,
        permissions={
            settings.get_value("guild_id"): [
                create_permission(
                    settings.get_value("role_staff"),
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
                create_permission(
                    settings.get_value("role_trial_mod"),
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
            ]
        },
    )
    async def refresh(self, ctx: SlashContext, user: discord.User = None):
        """A command to forcefully reload the user stats to add missing keys or remove deprecated keys."""
        await ctx.defer()

        # Connect to the database and get the achievement table.
        db = dataset.connect(database.get_db())
        achievements = db["achievements"]

        # Get the LevelingCog for utilities functions.
        leveling_cog = self.bot.get_cog("LevelingCog")

        # If the user is not specified, default it to a global command.
        if not user:
            # Iterate through all the entries in the database and add the missing or remove the deprecated keys.
            for entry in achievements:
                entry_stats = json.loads(entry["stats"])
                entry_stats = await leveling_cog.verify_integrity(entry_stats)
                entry_stats_json = json.dumps(entry_stats)
                achievements.update(
                    dict(id=entry["id"], stats=entry_stats_json), ["id"]
                )

            # Send an embed to notify when the task is done.
            embed = embeds.make_embed(
                description="Successfully reloaded all user stats.", color="green"
            )
            await ctx.send(embed=embed)

            # Commit the changes to the database and close it.
            db.commit()
            db.close()
            return

        # If we received an int instead of a discord.Member, the user is not in the server.
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        # Attempt to find the user who issued the command.
        user_entry = achievements.find_one(user_id=user.id)

        # Return if the user is not found in the database.
        if not user_entry:
            await embeds.error_message(
                ctx=ctx, description="Could not find the specified user."
            )
            db.close()
            return

        # Loads the JSON object in the database into a dictionary to manipulate.
        stats = json.loads(user_entry["stats"])

        # Check the integrity of the stats dictionary and add missing keys or remove deprecated keys.
        stats = await leveling_cog.verify_integrity(stats)

        # Dump the modified JSON into the db.
        stats_json = json.dumps(stats)
        achievements.update(dict(id=user_entry["id"], stats=stats_json), ["id"])

        # Send an embed to notify when the task is done.
        embed = embeds.make_embed(
            description=f"Successfully reloaded {user.mention}'s stats.", color="green"
        )
        await ctx.send(embed=embed)

        # Commit the changes to the database and close it.
        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    """Load the Console cog."""
    bot.add_cog(Console(bot))
    log.info("Commands loaded: console")
