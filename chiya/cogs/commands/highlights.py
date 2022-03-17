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
        "Sets a highlight to be notified when a message is sent in chat",
        guild_ids=config["guild_ids"],
    )

    @highlight.command(name="add", descrption="Adds a highlighted term to be track")
    async def add_highlight(
        self,
        ctx: context.ApplicationContext,
        term: Option(str, description="Term to be highlighted.", required=True),
    ) -> None:
        """
        Adds the user to the highlighted term list so they will be notified
        on subsquent messages containing the highlighted term.
        """
        await ctx.defer()

        db = database.Database().get()
        result = db['highlights'].find_one(term={"ilike": term})
        if result:
            users = orjson.loads(result["users"])
            if ctx.author.id not in users:
                users.append(ctx.author.id)
                data = dict(id=result['id'], users=orjson.dumps(users))
                db['highlights'].update(data, ["id"])
        else:
            data = dict(
                term=term,
                users=orjson.dumps([ctx.author.id])
            )
            db['highlights'].insert(data)

        refresh_cache()
        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            title='Highlight added',
            description=f'The term `{term}` was added to your highlights list.',
            color=discord.Color.green(),
            author=True
        )
        await ctx.send_followup(embed=embed)

    @highlight.command(name="list", descrption="Lists the highlighted terms you're currently tracking")
    async def list_highlights(
        self,
        ctx: context.ApplicationContext
    ) -> None:
        """
        Renders a list showing all of the terms that the user currently has
        highlighted to be notified on usage of.
        """
        await ctx.defer()

        db = database.Database().get()
        results = db['highlights'].find(users={"ilike": f"%{ctx.author.id}%"})

        embed = embeds.make_embed(
            ctx=ctx,
            title="You're currently tracking the following words:",
            description="\n".join([str(term["term"]) for term in results]),
            color=discord.Color.green(),
            author=True
        )
        db.close()
        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(HighlightCommands(bot))
    log.info("Commands loaded: highlights")
