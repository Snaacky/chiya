import asyncio
import logging

import discord
from discord.commands import Option, SlashCommandGroup, context, slash_command
from discord.ext import commands
import orjson
from sqlalchemy import desc

from chiya import config, database
from chiya.utils import embeds
from chiya.utils.highlights import refresh_cache
from chiya.utils.pagination import LinePaginator


log = logging.getLogger(__name__)


class HighlightCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    highlight = SlashCommandGroup(
        "hl",
        "Sets a highlight to be notified when a message is sent in chat.",
        guild_ids=config["guild_ids"],
    )

    @highlight.command(name="add", descrption="Adds a highlight to track.")
    async def add_highlight(
        self,
        ctx: context.ApplicationContext,
        highlighted_term: Option(str, description="Term to be highlighted.", required=True),
    ) -> None:
        """
        Add a highlight.
        """
        await ctx.defer()

        db = database.Database().get()
        highlights = db['highlights']
        result = highlights.find_one(highlighted_term={"ilike": highlighted_term})
        if result:
            subscribed_users = orjson.loads(result['subscribed_users'])
            if ctx.author.id not in subscribed_users:
                subscribed_users.append(ctx.author.id)
                data = dict(id=result['id'], subscribed_users=orjson.dumps(subscribed_users))
                highlights.update(data, ["id"])
        else:
            data = dict(
                highlighted_term=highlighted_term, 
                subscribed_users=orjson.dumps([ctx.author.id])
            )
            highlights.insert(data)
        
        refresh_cache()
        db.commit()
        db.close()
        
        
        embed = embeds.make_embed(
            ctx=ctx,
            title='Highlight added',
            description=f'The term `{highlighted_term}` was added to your highlights list.',
            color=discord.Color.green(),
            author=True
        )
        await ctx.send_followup(embed=embed)
    
            

def setup(bot: commands.Bot) -> None:
    bot.add_cog(HighlightCommands(bot))
    log.info("Commands loaded: highlights")
