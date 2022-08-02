import logging
import time

import discord
from discord.commands import Option, context, slash_command, SlashCommandGroup
from discord.ext import commands

from chiya import config, database
from chiya.utils import embeds
from chiya.utils.pagination import LinePaginator


log = logging.getLogger(__name__)


class AutomodCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    automod = SlashCommandGroup(
        "automod",
        "Manage terms added to the AutoMod",
        guild_ids=config["guild_ids"],
    )

    @automod.command(guild_ids=config["guild_ids"], description="Adds a word to the AutoMod on the server.")
    @commands.has_any_role(config["roles"]["staff"])
    async def add_word(
        self,
        ctx: context.ApplicationContext,
        automod_term: Option(str, description="The word that is to be automodded (supports wildcards)"),
    ):
        """
        Add a word to the AutoMod.
        """
        await ctx.defer()
        automod_term = automod_term.lower()
        automod_rule = await ctx.guild.fetch_auto_moderation_rule(id=config["automod"]["words"])
        if automod_term not in automod_rule.trigger_metadata.keyword_filter:
            automod_rule.trigger_metadata.keyword_filter.append(automod_term) 
            await automod_rule.edit(trigger_metadata=automod_rule.trigger_metadata, reason=f"Add word: {automod_term} to automod.")
        
        await ctx.send_followup(f"Added word: `{automod_term}` to automod.")
    
    @automod.command(guild_ids=config["guild_ids"], description="Adds a link to the AutoMod on the server.")
    @commands.has_any_role(config["roles"]["staff"])
    async def add_link(
        self,
        ctx: context.ApplicationContext,
        automod_term: Option(str, description="The link that is to be automodded"),
    ):
        """
        Add a link to the AutoMod.
        """
        await ctx.defer()
        automod_term = automod_term.lower()
        automod_rule = await ctx.guild.fetch_auto_moderation_rule(id=config["automod"]["links"])
        if automod_term not in automod_rule.trigger_metadata.keyword_filter:
            automod_rule.trigger_metadata.keyword_filter.append(automod_term) 
            await automod_rule.edit(trigger_metadata=automod_rule.trigger_metadata, reason=f"Add link: {automod_term} to automod.")
        
        await ctx.send_followup(f"Added link: `{automod_term}` to automod.")
    
    @automod.command(guild_ids=config["guild_ids"], description="Lists all the automodded terms.")
    @commands.has_any_role(config["roles"]["staff"])
    async def list_terms(
        self,
        ctx: context.ApplicationContext,
        category: Option(str, choices=["words", "links"], required=True)
    ):
        """
        List all the currently automodded terms
        """
        await ctx.defer()
        automod_rule = await ctx.guild.fetch_auto_moderation_rule(id=config["automod"][category])
        embed = embeds.make_embed(ctx=ctx, author=ctx.author, title=f"List of automodded {category}", color=discord.Color.blurple)
        term_list = [f"`{term}`" for term in automod_rule.trigger_metadata.keyword_filter]
        await LinePaginator.paginate(
            lines=term_list,
            ctx=ctx,
            embed=embed,
            max_lines=10,
            max_size=2000,
            linesep="\n",
            timeout=120,
        )

    @automod.command(guild_ids=config["guild_ids"], description="Removes a word from the AutoMod on the server.")
    @commands.has_any_role(config["roles"]["staff"])
    async def remove_word(
        self,
        ctx: context.ApplicationContext,
        automod_term: Option(str, description="The word that is to be removed from automod"), 
    ):
        """
        Remove a term from AutoMod
        """
        await ctx.defer()
        automod_term = automod_term.lower()
        automod_rule = await ctx.guild.fetch_auto_moderation_rule(id=config["automod"]["words"])
        if automod_term not in automod_rule.trigger_metadata.keyword_filter:
            automod_rule.trigger_metadata.keyword_filter.remove(automod_term) 
            await automod_rule.edit(trigger_metadata=automod_rule.trigger_metadata, reason=f"Remove word: {automod_term} from automod.")
        
        await ctx.send_followup(f"Removed word: `{automod_term}` from automod.")
    
    @automod.command(guild_ids=config["guild_ids"], description="Removes a link from the AutoMod on the server.")
    @commands.has_any_role(config["roles"]["staff"])
    async def remove_link(
        self,
        ctx: context.ApplicationContext,
        automod_term: Option(str, description="The link that is to be removed from automod"), 
    ):
        """
        Remove a link from AutoMod
        """
        await ctx.defer()
        automod_term = automod_term.lower()
        automod_rule = await ctx.guild.fetch_auto_moderation_rule(id=config["automod"]["links"])
        if automod_term not in automod_rule.trigger_metadata.keyword_filter:
            automod_rule.trigger_metadata.keyword_filter.remove(automod_term) 
            await automod_rule.edit(trigger_metadata=automod_rule.trigger_metadata, reason=f"Remove link: {automod_term} from automod.")
        
        await ctx.send_followup(f"Removed link: `{automod_term}` from automod.")

def setup(bot: commands.Bot) -> None:
    bot.add_cog(AutomodCommands(bot))
    log.info("Commands loaded: automod")
