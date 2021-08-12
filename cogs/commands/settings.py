import logging

import dataset
from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission

from utils import database
from utils import embeds
from utils.database import get_db

log = logging.getLogger(__name__)


def get_value(config: str):
    # Get all of the settings from the table and load them into the dictionary.
    db = dataset.connect(get_db())
    data = db["settings"].all()

    # Iterate through database entries and add them as a dictionary.
    settings = {}
    for setting in data:
        settings[setting["name"]] = {"value": setting["value"], "censored": bool(setting["censored"])}

    # If the entry's value consists of only numbers, return it as an int.
    if settings[config]["value"].isdecimal():
        db.close()
        return int(settings[config]["value"])

    # Otherwise, return the value normally (as a string by default).
    db.close()
    return settings[config]["value"]


class Settings(Cog):
    """ General Commands Cog """

    def __init__(self, bot: Bot):
        self.bot = bot

    @cog_ext.cog_subcommand(
        base="settings",
        name="add",
        description="Add a new setting to the database",
        guild_ids=[get_value("guild_id")],
        base_default_permission=False,
        options=[
            create_option(
                name="name",
                description="The name of the setting to be added",
                option_type=3,
                required=True
            ),
            create_option(
                name="value",
                description="The value for the setting to be added",
                option_type=3,
                required=False
            ),
            create_option(
                name="censored",
                description="Whether or not the value should be censored when displayed",
                option_type=5,
                required=False
            ),
        ],
        base_permissions={
            get_value("guild_id"): [
                create_permission(get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
            ]
        }
    )
    async def add(self, ctx: SlashContext, name: str, value: str, censored: bool):
        # Open a connection to the database.
        db = dataset.connect(database.get_db())
        table = db["settings"]
        result = table.find_one(name=name)

        # Error if a setting already exists with that name.
        if result:
            embed = embeds.make_embed(description="A setting with that name already exists.", color="soft_red")
            await ctx.send(embed=embed)
            return

        # Add the setting to the database.
        table.insert(dict(
            name=name,
            value=value,
            censored=censored
        ))

        # Send a confirmation embed to the command invoker.
        embed = embeds.make_embed(description=f"Added '{name}' to the database.", color="soft_green")

        # Hides the command invokation if the censored parameter was used.
        if censored:
            await ctx.send(embed=embed, hidden=True)
        else:
            await ctx.send(embed=embed)

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

    @cog_ext.cog_subcommand(
        base="settings",
        name="edit",
        description="Edit an existing setting in the database",
        guild_ids=[get_value("guild_id")],
        base_default_permission=False,
        options=[
            create_option(
                name="name",
                description="The name of the setting to be edited",
                option_type=3,
                required=True
            ),
            create_option(
                name="value",
                description="The updated value for the setting",
                option_type=3,
                required=True
            ),
            create_option(
                name="censored",
                description="The updated value for the censored value",
                option_type=5,
                required=False
            ),
        ],
        base_permissions={
            get_value("guild_id"): [
                create_permission(get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
            ]
        }
    )
    async def edit(self, ctx: SlashContext, name: str, value: str, censored: bool = None):
        await ctx.defer()

        # Open a connection to the database.
        db = dataset.connect(database.get_db())
        table = db["settings"]
        result = table.find_one(name=name)

        # Error if a setting does not exist with that name.
        if not result:
            embed = embeds.make_embed(description="A setting with that name does not exist.", color="soft_red")
            await ctx.send(embed=embed)
            return

        # Update the value(s) in the database.
        result["value"] = value

        # Only update the censored value if the user specified the optional parameter.
        if censored is not None:
            result["censored"] = censored
        table.update(result, ["id"])

        # Send a confirmation embed to the command invoker.
        embed = embeds.make_embed(description=f"Updated '{name}' in the database.", color="soft_green")
        await ctx.send(embed=embed)

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

    @cog_ext.cog_subcommand(
        base="settings",
        name="delete",
        description="Delete an existing setting from the database",
        guild_ids=[get_value("guild_id")],
        base_default_permission=False,
        options=[
            create_option(
                name="name",
                description="The name of the setting to be edited",
                option_type=3,
                required=True
            )
        ],
        base_permissions={
            get_value("guild_id"): [
                create_permission(get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
            ]
        }
    )
    async def delete(self, ctx: SlashContext, name: str):
        # Open a connection to the database.
        db = dataset.connect(database.get_db())
        table = db["settings"]
        result = table.find_one(name=name)

        # Error if a setting does not exist with that name.
        if not result:
            embed = embeds.make_embed(description="A setting with that name does not exist.", color="soft_red")
            await ctx.send(embed=embed)
            return

        # Delete the setting from the database.
        table.delete(name=name)

        # Send a confirmation embed to the command invoker.
        embed = embeds.make_embed(description=f"Deleted '{name}' from the database.", color="soft_green")
        await ctx.send(embed=embed)

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

    @cog_ext.cog_subcommand(
        base="settings",
        name="list",
        description="Lists all of the settings in the database",
        guild_ids=[get_value("guild_id")],
        base_default_permission=False,
        base_permissions={
            get_value("guild_id"): [
                create_permission(get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
            ]
        }
    )
    async def list(self, ctx: SlashContext):
        # Open a connection to the database.
        db = dataset.connect(database.get_db())
        table = db["settings"]
        settings = table.all()

        # Append all of the setting names to a list.
        names = [setting["name"] for setting in settings]

        # Error if the list is empty because it means the table is empty.
        if not names:
            embed = embeds.make_embed(description="Unable to find any settings in the database.", color="soft_red")
            await ctx.send(embed=embed)
            return

        # Format the list entries into inline codeblocks for the embed.
        names = f", ".join(f'`{name}`' for name in names)

        # Create and send the embed containing the settings list to the command invoker.
        embed = embeds.make_embed(description=f"Found the following settings: {names}", color="soft_green")
        await ctx.send(embed=embed)

        # Close the connection to the database.
        db.close()

    @cog_ext.cog_subcommand(
        base="settings",
        name="view",
        description="View the current values for a setting",
        guild_ids=[get_value("guild_id")],
        base_default_permission=False,
        options=[
            create_option(
                name="name",
                description="The name of the setting to be viewed",
                option_type=3,
                required=True
            )
        ],
        base_permissions={
            get_value("guild_id"): [
                create_permission(get_value("role_staff"), SlashCommandPermissionType.ROLE, True),
            ]
        }
    )
    async def view(self, ctx: SlashContext, name: str):
        # Open a connection to the database.
        db = dataset.connect(database.get_db())
        table = db["settings"]
        result = table.find_one(name=name)

        # Error if a setting does not exist with that name.
        if not result:
            embed = embeds.make_embed(description="A setting with that name does not exist.", color="soft_red")
            await ctx.send(embed=embed)
            return

        # If the value is set to censored in the database, censor all but the first and last characters.
        if result.get("censored"):
            value = result['value'][:1] + "\*" * (len(result['value']) - 2) + result['value'][-1:]
        else:
            value = result["value"]

        # Create and send the embed containing the setting data to the command invoker.
        embed = embeds.make_embed(title=result['name'])
        embed.add_field(name="Name:", value=result['name'], inline=False)
        embed.add_field(name="Value:", value=value, inline=False)
        embed.add_field(name="Censored:", value=str(bool(result["censored"])), inline=False)
        await ctx.send(embed=embed)

        # Close the connection to the database.
        db.close()


def setup(bot: Bot) -> None:
    """ Load the Settings cog. """
    bot.add_cog(Settings(bot))
    log.info("Commands loaded: Settings")
