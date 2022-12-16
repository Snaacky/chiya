import logging

import discord
import orjson
from discord import app_commands
from discord.ext import commands


from chiya import config, database
from chiya.utils import embeds


log = logging.getLogger(__name__)


class HighlightCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    class HighlightGroup(app_commands.Group):
        pass
    highlight = HighlightGroup(name="hl", description="Highlight management commands", guild_ids=[config["guild_id"]])

    @highlight.command(name="add", description="Adds a term to be tracked")
    @app_commands.describe(term="Term to be highlighted")
    async def add_highlight(
        self,
        ctx: discord.Interaction,
        term: str,
    ) -> None:
        """
        Adds the user to the highlighted term list so they will be notified
        on subsquent messages containing the highlighted term.
        """
        await ctx.response.defer(thinking=True)

        # Prevent /hl list from being extra long and being unable to be sent.
        if len(term) > 50:
            return await embeds.error_message(ctx=ctx, description="Highlighted terms must be less than 50 characters.")

        db = database.Database().get()

        # 20 term limit because 20 * 50 = 1000 characters max and embeds are 4096 max.
        total = [result for result in db["highlights"].find(users={"ilike": f"%{ctx.user.id}%"})]
        if len(total) >= 20:
            return await embeds.error_message(
                ctx=ctx, description="You may only have up to 20 highlighted terms at once."
            )

        result = db["highlights"].find_one(term={"ilike": term})
        if result:
            users = orjson.loads(result["users"])
            if ctx.user.id not in users:
                users.append(ctx.user.id)
                data = dict(id=result["id"], users=orjson.dumps(users))
                db["highlights"].update(data, ["id"])
        else:
            data = dict(term=term, users=orjson.dumps([ctx.user.id]))
            db["highlights"].insert(data)

        db.commit()
        db.close()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Highlight added",
            description=f"The term `{term}` was added to your highlights list.",
            color=discord.Color.green(),
            author=True,
        )
        await ctx.followup.send(embed=embed)
        highlights = self.bot.get_cog("HighlightsListener")
        highlights.refresh_highlights()

    @highlight.command(name="list", description="Lists the terms you're currently tracking")
    async def list_highlights(self, ctx: discord.Interaction) -> None:
        """
        Renders a list showing all of the terms that the user currently has
        highlighted to be notified on usage of.
        """
        await ctx.response.defer(thinking=True)

        db = database.Database().get()
        results = [result for result in db["highlights"].find(users={"ilike": f"%{ctx.user.id}%"})]
        if not results:
            return await embeds.error_message(ctx=ctx, description="You are not tracking any terms.")

        embed = embeds.make_embed(
            ctx=ctx,
            title="You're currently tracking the following words:",
            description="\n".join([str(term["term"]) for term in results]),
            color=discord.Color.green(),
            author=True,
        )
        db.close()
        await ctx.followup.send(embed=embed)

    @highlight.command(name="remove", description="Remove a term from being tracked")
    @app_commands.describe(term="Term to be removed")
    async def remove_highlight(
        self,
        ctx: discord.Interaction,
        term: str,
    ) -> None:
        await ctx.response.defer(thinking=True)

        db = database.Database().get()
        result = db["highlights"].find_one(term=term, users={"ilike": f"%{ctx.user.id}%"})

        if not result:
            return await embeds.error_message(ctx=ctx, description="You are not tracking that term.")

        users = orjson.loads(result["users"])
        users.remove(ctx.user.id)
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
            author=True,
        )
        await ctx.followup.send(embed=embed)
        highlights = self.bot.get_cog("HighlightsListener")
        highlights.refresh_highlights()

    @highlight.command(name="clear", description="Clears all terms being tracked")
    async def clear_highlights(self, ctx: discord.Interaction) -> None:
        await ctx.response.defer(thinking=True)

        db = database.Database().get()
        results = [result for result in db["highlights"].find(users={"ilike": f"%{ctx.user.id}%"})]

        if not results:
            return await embeds.error_message(ctx=ctx, description="You are not tracking any terms.")

        for result in results:
            users = orjson.loads(result["users"])
            users.remove(ctx.user.id)
            db["highlights"].update(dict(id=result["id"], users=orjson.dumps(users)), ["id"])

            # Delete the term from the database if no users are tracking the keyword anymore.
            if not len(users):
                db["highlights"].delete(term=result["term"])

        db.commit()
        db.close()
        highlights = self.bot.get_cog("HighlightsListener")
        highlights.refresh_highlights()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Highlights cleared",
            description="All of the terms in your highlight list were cleared.",
            color=discord.Color.green(),
            author=True,
        )
        await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HighlightCommands(bot))
    log.info("Commands loaded: highlight")
