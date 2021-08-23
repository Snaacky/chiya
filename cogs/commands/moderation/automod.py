import asyncio
import logging
from typing import List


import dataset
from discord_slash.context import ComponentContext
from sqlalchemy.sql.expression import desc

import config
from utils import database

from discord.ext import commands
import discord
from discord.ext.commands.core import group
from utils import embeds
from utils.record import record_usage
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_permission

from discord_slash.model import SlashCommandPermissionType
from utils.pagination import LinePaginator


# Enabling logs
log = logging.getLogger(__name__)


class AutomodCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="automod",
        name = "list",
        description="Lists all the currently censored terms.",
        guild_ids=[config.guild_id],
        options = [
            create_option(
                name="censor_type",
                option_type = 3,
                description="The censor type. Can be regex, links, fuzzy, substring or exact.",
                required=False
            )
        ],
        base_default_permission=False,
        base_permissions={
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
                create_permission(config.role_trial_mod, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def list_censors(self, ctx: SlashContext, censor_type: str = None):
        await ctx.defer()
        
        censored_terms = []
        db = dataset.connect(database.get_db())
        censors = None
        if not censor_type:
            censors = db['censor'].all()
        else:
            censors = db['censor'].find(
                censor_type = censor_type
            )
        
        for censor in censors:
            censor_term = censor['censor_term']
            if censor['censor_type'] == 'fuzzy':
                censor_term = f"{censor['censor_term']} ({censor['censor_threshold']}%)"
            censored_term = f"**ID: {censor['id']} ** | **{censor['censor_type']}**\n```{censor_term}```"
            censored_terms.append(censored_term)
        
        embed = embeds.make_embed(ctx=ctx, title = "Censored Terms", thumbnail_url=config.defcon_disabled, color="gold")

        await LinePaginator.paginate(censored_terms, ctx=ctx, embed=embed, max_lines=5, max_size=2000, time_to_delete=30)

        db.close()

    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="automod",
        name = "add",
        description="Adds a term to the censor list.",
        guild_ids=[config.guild_id],
        options = [
            create_option(
                name="censor_type",
                option_type = 3,
                description="The censor type. Can be regex, links, fuzzy, substring or exact.",
                required=True
            ),
            create_option(
                name="censor_term",
                option_type = 3,
                description="The censor term.",
                required=True
            ),
            create_option(
                name="censor_threshold",
                option_type = 4,
                description="The censor treshold (only for fuzzy).",
                required=False
            )
        ],
        base_default_permission=False,
        base_permissions={
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
                create_permission(config.role_trial_mod, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def add_censor(self, ctx: SlashContext, censor_type: str, censor_term: str, censor_threshold: int = 0):
        await ctx.defer()

        censor_types = [
            {
                "name": "substring",
                "aliases": ['substr', 'sub', 's']
            },
            {
                "name": "regex",
                "aliases": ['r']
            },
            {
                "name": "exact",
                "aliases": ['e']
            },
            {
                "name": "links",
                "aliases": ['link', 'l']
            },
            {
                "name": "fuzzy",
                "aliases": ['fuz', 'f']
            }
        ]
         # sanitizing input
        censor_type = censor_type.lower()
        censor_type = censor_type.strip()
        censor_term = censor_term.strip()
        if not censor_threshold:
            censor_threshold = 65 # default set, since this seems to work fine
        for x in censor_types:
            if (censor_type == x['name'] or censor_type in x['aliases']):
                # adding to the DB and messaging user that action was successful

                if (x['name'] == 'fuzzy'):
                        # in case user enters a threshold value > 100.
                        if (censor_threshold>100):
                            await embeds.error_message(description="Fuzziness threshold must be less than 100!", ctx=ctx)
                            return

                db = dataset.connect(database.get_db())
                db['censor'].insert(dict(
                    censor_term=censor_term,
                    censor_type=x['name'],
                    censor_threshold=censor_threshold
                ))
                
                db.commit()
                db.close()

                embed = embeds.make_embed(ctx=ctx, description=f"Censor term `{censor_term}` of type `{x['name']}` was added.", color="green")
                await ctx.send(embed=embed)
                return


        # User did not specify censor type properly, so throw an error.
        await embeds.error_message(description="Valid censor types are: `substring`, `regex`, `exact`, `links` and `fuzzy`.", ctx=ctx)
    
    @commands.before_invoke(record_usage)
    @cog_ext.cog_subcommand(
        base="automod",
        name = "remove",
        description="Removes a term from the censor list.",
        guild_ids=[config.guild_id],
        options = [
            create_option(
                name="id",
                option_type = 4,
                description="ID of the censored term.",
                required=True
            )
        ],
        base_default_permission=False,
        base_permissions={
            config.guild_id: [
                create_permission(config.role_staff, SlashCommandPermissionType.ROLE, True),
                create_permission(config.role_trial_mod, SlashCommandPermissionType.ROLE, True)
            ]
        }
    )    
    async def remove_censor(self, ctx: SlashContext, id: int):
        await ctx.defer()
        
        db = dataset.connect(database.get_db())
        censor = db['censor'].find_one(id=id)
        
        if not censor:
            await embeds.error_message(ctx=ctx, description="The censor with that ID does not exist!")
            return
        
        db['censor'].delete(id=id)
        db.commit()
        db.close()

        embed = embeds.make_embed(ctx=ctx, description=f"Term `{censor['censor_term']}` of type `{censor['censor_type']}` was deleted.", color='red')
        await ctx.send(embed=embed)
            
def setup(bot) -> None:
    bot.add_cog(AutomodCog(bot))
    log.info("Cog loaded: AutomodCog")
