import logging

import discord
from discord.commands import Option, SlashCommandGroup, context
from discord.ext import commands
import orjson

from chiya import config, database
from chiya.utils import embeds


log = logging.getLogger(__name__)


class HighlightCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    highlight = SlashCommandGroup(
        "hl",
        "Sets a highlight to be notified when a message is sent in chat",
        guild_ids=config["guild_ids"],
    )

    @highlight.command(name="add", description="Adds a term to be tracked")
    async def add_highlight(
        self,
        ctx: context.ApplicationContext,
        term: Option(str, description="Term to be highlighted", required=True),
    ) -> None:
        """
        Adds the user to the highlighted term list so they will be notified
        on subsquent messages containing the highlighted term.
        """
        await ctx.defer()

        # 50 character limit prevents the /hl list embed from ever overflowing and causing it to be unable to be sent.
        if len(term) > 50:
            return await embeds.error_message(ctx=ctx, description="Highlighted terms must be less than 50 characters.")

        db = database.Database().get()

        # 20 term limit prevents the same as the above because 20 * 50 = 1000 characters max and embeds are 4096 max.
        total = [result for result in db["highlights"].find(users={"ilike": f"%{ctx.author.id}%"})]
        if len(total) >= 20:
            return await embeds.error_message(ctx=ctx, description="You may only have up to 20 highlighted terms at once.")

        result = db["highlights"].find_one(term={"ilike": term})
        if result:
            users = orjson.loads(result["users"])
            if ctx.author.id not in users:
                users.append(ctx.author.id)
                data = dict(id=result["id"], users=orjson.dumps(users))
                db["highlights"].update(data, ["id"])
        else:
            data = dict(
                term=term,
                users=orjson.dumps([ctx.author.id])
            )
            db["highlights"].insert(data)

        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Highlight added",
            description=f"The term `{term}` was added to your highlights list.",
            color=discord.Color.green(),
            author=True
        )
        await ctx.send_followup(embed=embed)

    @highlight.command(name="list", description="Lists the terms you're currently tracking")
    async def list_highlights(
        self,
        ctx: context.ApplicationContext
    ) -> None:
        """
        Renders a list showing all of the terms that the user currently has
        highlighted to be notified on usage of.
        """
        # This has very inconsistent output and the if not results check does not seem to work consistently.
        await ctx.defer()

        db = database.Database().get()
        results = [result for result in db["highlights"].find(users={"ilike": f"%{ctx.author.id}%"})]
        if not results:
            return await embeds.error_message(ctx=ctx, description="You are not tracking any terms.")

        embed = embeds.make_embed(
            ctx=ctx,
            title="You're currently tracking the following words:",
            description="\n".join([str(term["term"]) for term in results]),
            color=discord.Color.green(),
            author=True
        )
        db.close()
        await ctx.send_followup(embed=embed)

    @highlight.command(name="remove", description="Remove a term from being tracked")
    async def remove_highlight(
        self,
        ctx: context.ApplicationContext,
        term: Option(str, description="Term to be removed", required=True),
    ) -> None:
        await ctx.defer()

        db = database.Database().get()
        result = db["highlights"].find_one(term=term, users={"ilike": f"%{ctx.author.id}%"})

        if not result:
            return await embeds.error_message(ctx=ctx, description="You are not tracking that term.")

        users = orjson.loads(result["users"])
        users.remove(ctx.author.id)
        db["highlights"].update(dict(id=result["id"], users=orjson.dumps(users)), ["id"])

        # Delete the term from the database if no users are tracking the keyword anymore.
        if not len(users):
            db["highlights"].delete(term=term)

        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Highlight removed",
            description=f"The term `{term}` was removed from your highlights list.",
            color=discord.Color.green(),
            author=True
        )
        await ctx.send_followup(embed=embed)

    @highlight.command(name="clear", description="Clears all terms being tracked")
    async def clear_highlights(
        self,
        ctx: context.ApplicationContext
    ) -> None:
        await ctx.defer()

        db = database.Database().get()
        results = [result for result in db["highlights"].find(users={"ilike": f"%{ctx.author.id}%"})]

        if not results:
            return await embeds.error_message(ctx=ctx, description="You are not tracking any terms.")

        for result in results:
            users = orjson.loads(result["users"])
            users.remove(ctx.author.id)
            db["highlights"].update(dict(id=result["id"], users=orjson.dumps(users)), ["id"])

            # Delete the term from the database if no users are tracking the keyword anymore.
            if not len(users):
                db["highlights"].delete(term=result["term"])

        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Highlights cleared",
            description="All of the terms in your highlight list were cleared.",
            color=discord.Color.green(),
            author=True
        )
        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(HighlightCommands(bot))
    log.info("Commands loaded: highlights")
