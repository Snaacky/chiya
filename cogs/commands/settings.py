import logging

import dataset
from discord.ext.commands import Bot, Cog

import config
from utils import database
from utils import embeds
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_permission
from discord_slash.model import SlashCommandPermissionType

log = logging.getLogger(__name__)

class Settings(Cog):
    """ General Commands Cog """

    def __init__(self, bot: Bot):
        self.bot = bot

    @cog_ext.cog_subcommand(
        base="settings",
        name="add",
        description="Add a new setting to the database",
        guild_ids=[config.guild_id],
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
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
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
        await ctx.send(embed=embed)

        # Commit the changes to the database and close the connection.
        db.commit()
        db.close()

    @cog_ext.cog_subcommand(
        base="settings",
        name="delete",
        description="Delete an existing setting from the database",
        guild_ids=[config.guild_id],
        base_default_permission=False,
        options=[
            create_option(
                name="name",
                description="The name of the constant to be edited",
                option_type=3,
                required=True
            )
        ],
        base_permissions={
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
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


def setup(bot: Bot) -> None:
    """ Load the Settings cog. """
    bot.add_cog(Settings(bot))
    log.info("Commands loaded: Settings")
