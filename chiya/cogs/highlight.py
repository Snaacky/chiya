import re
from datetime import datetime, timedelta

import discord
from collections import defaultdict
from discord import app_commands
from discord.ext import commands
from loguru import logger

from chiya.config import config
from chiya.models import Highlight
from chiya.utils import embeds


class HighlightCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.refresh_highlights()

    def refresh_highlights(self) -> None:
        self.highlights = defaultdict(set)
        for highlight in Highlight.query.all():
            self.highlights[highlight.term].add(highlight.user_id)

    @app_commands.guilds(config.guild_id)
    @app_commands.guild_only()
    class HighlightGroup(app_commands.Group):
        pass

    highlight = HighlightGroup(name="hl", description="Highlight management commands", guild_ids=[config.guild_id])

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Scan incoming messages for highlights and notify the subscribed users.
        """
        if message.author.bot:
            return

        # These are set as None here to reduce the number of queries to discord
        # We only want to fetch this data when we have a match otherwise we will
        # fetch this data every message which gets us rate limited
        active_members, chat = None, None

        for term, users in self.highlights.items():
            regex = rf"\b{re.escape(term)}\b"
            result = re.search(regex, message.clean_content, re.IGNORECASE)

            if not result:
                continue

            if active_members is None:
                active_members = await self.active_members(message.channel)

            if chat is None:
                messages = [for_message async for for_message in message.channel.history(limit=4, before=message)]
                chat = ""
                for msg in reversed(messages):
                    chat += f"**[<t:{int(msg.created_at.timestamp())}:T>] {msg.author.name}:** {msg.clean_content[0:256]}\n"
                chat += f"✨ **[<t:{int(message.created_at.timestamp())}:T>] {message.author.name}:** \
                    {message.clean_content[0:256]}\n"

            embed = embeds.make_embed(title=term, description=chat, color=discord.Color.gold())
            embed.add_field(name="Source Message", value=f"[Jump to]({message.jump_url})")

            for subscriber in users:
                if subscriber == message.author.id or subscriber in active_members:
                    continue

                try:
                    member = await message.guild.fetch_member(subscriber)
                except discord.errors.NotFound:
                    logger.debug(f"Attempting to find member failed: {subscriber}")
                    continue

                if not message.channel.permissions_for(member).view_channel:
                    continue

                try:
                    channel = await member.create_dm()
                    await channel.send(
                        content=(
                            f"You were mentioned with the highlight term `{term}` "
                            f"in **{message.guild.name}** {message.channel.mention}."
                        ),
                        embed=embed,
                    )
                except discord.Forbidden:
                    pass

    @highlight.command(name="add", description="Adds a term to be tracked")
    @app_commands.describe(term="Term to be highlighted")
    async def add_highlight(self, ctx: discord.Interaction, term: str) -> None:
        """
        Adds the user to the highlighted term list so they will be notified
        on subsquent messages containing the highlighted term.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        # Prevent /hl list from being extra long and being unable to be sent.
        if len(term) > 50:
            return await embeds.send_error(ctx=ctx, description="Highlighted terms must be less than 50 characters.")

        # 20 term limit because 20 * 50 = 1000 characters max and embeds are 4096 max.
        if Highlight.query.filter_by(user_id=ctx.user.id).count() >= 20:
            return await embeds.send_error(
                ctx=ctx,
                description="You may only have up to 20 highlighted terms at once.",
            )

        # Prevent users from tracking the same term more than once.
        if Highlight.query.filter_by(user_id=ctx.user.id, term=term).first():
            return await embeds.send_error(ctx=ctx, description="You are already tracking that term.")

        row = Highlight(user_id=ctx.user.id, term=term).save()
        self.refresh_highlights()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Highlight added",
            description=f"The term `{row.term}` was added to your highlights list.",
            color=discord.Color.green(),
            author=True,
        )
        await ctx.followup.send(embed=embed)

    @highlight.command(name="list", description="Lists the terms you're currently tracking")
    async def list_highlights(self, ctx: discord.Interaction) -> None:
        """
        Renders a list showing all of the terms that the user currently has
        highlighted to be notified on usage of.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not (results := Highlight.query.filter_by(user_id=ctx.user.id)):
            return await embeds.send_error(ctx=ctx, description="You are not tracking any terms.")

        embed = embeds.make_embed(
            ctx=ctx,
            title="You're currently tracking the following words:",
            description="\n".join([str(row.term) for row in results]),
            color=discord.Color.green(),
            author=True,
        )
        await ctx.followup.send(embed=embed)

    @highlight.command(name="remove", description="Remove a term from being tracked")
    @app_commands.describe(term="Term to be removed")
    async def remove_highlight(
        self,
        ctx: discord.Interaction,
        term: str,
    ) -> None:
        await ctx.response.defer(thinking=True, ephemeral=True)

        result = Highlight.query.filter_by(user_id=ctx.user.id, term=term).first()
        if not result:
            return await embeds.send_error(ctx=ctx, description="You are not tracking that term.")

        result.delete()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Highlight removed",
            description=f"The term `{term}` was removed from your highlights list.",
            color=discord.Color.green(),
            author=True,
        )
        await ctx.followup.send(embed=embed)
        self.listener.refresh_highlights()

    @highlight.command(name="clear", description="Clears all terms being tracked")
    async def clear_highlights(self, ctx: discord.Interaction) -> None:
        await ctx.response.defer(thinking=True, ephemeral=True)

        results = Highlight.query.filter_by(user_id=ctx.user.id).all()
        if not results:
            return await embeds.send_error(ctx=ctx, description="You are not tracking any terms.")

        for result in results:
            result.delete()

        self.listener.refresh_highlights()

        embed = embeds.make_embed(
            ctx=ctx,
            title="Highlights cleared",
            description="All of the terms in your highlight list were cleared.",
            color=discord.Color.green(),
            author=True,
        )
        await ctx.followup.send(embed=embed)

    async def active_members(self, channel: discord.TextChannel) -> set:
        """
        Returns a set of all the active members in a channel.
        """
        after = datetime.now() - timedelta(minutes=config.hl.timeout)
        message_auths = set([message.author.id async for message in channel.history(after=after)])
        return message_auths


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HighlightCog(bot))
