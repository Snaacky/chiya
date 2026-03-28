import discord
from discord import app_commands
from discord.ext import commands

from chiya.config import config
from chiya.utils import embeds
from chiya.utils.helpers import log_embed_to_channel


class PurgeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def can_purge_messages(self, ctx: discord.Interaction) -> bool:
        """
        Check used by purge function to make sure that the moderation,
        development, logs, and tickets categories can't be purged for
        security reasons.
        """
        if not ctx.guild or not ctx.guild.owner:
            return False

        if ctx.user.id == ctx.guild.owner.id:
            return True

        if not isinstance(ctx.channel, discord.TextChannel):
            return False

        if ctx.channel.category_id in [
            config.categories.moderation,
            config.categories.development,
            config.categories.logs,
            config.categories.tickets,
        ]:
            return False

        return True

    @app_commands.command(name="purge", description="Purge the last X amount of messages")
    @app_commands.guilds(config.guild_id)
    @app_commands.checks.has_role(config.roles.staff)
    @app_commands.describe(amount="The amount of messages to be purged")
    @app_commands.describe(reason="The reason why the messages are being purged")
    async def purge(self, ctx: discord.Interaction, amount: int, reason: str) -> None:
        """
        Removes the last X amount of messages in bulk.

        Capped at a maximum of 100 messages per command invoke to avoid
        accidents wiping out large chunks of messages.

        Cannot be used in the moderation, development, logs, or archive
        categories for security reasons.
        """
        await ctx.response.defer(thinking=True)

        if not isinstance(ctx.channel, discord.TextChannel):
            return await embeds.send_error(ctx=ctx, description="This command can only be used in text channels.")

        if not self.can_purge_messages(ctx):
            return await embeds.send_error(ctx=ctx, description="You cannot use that command in this category.")

        if len(reason) > 4096:
            return await embeds.send_error(ctx=ctx, description="Reason must be less than 4096 characters.")

        amount = 100 if amount > 100 else amount

        embed = discord.Embed()
        embed.title = "Purged messages"
        embed.description = f"{ctx.user.mention} purged {amount} message(s) in {ctx.channel.mention}."
        embed.color = discord.Color.red()
        embed.add_field(name="Reason:", value=reason, inline=False)
        embed.set_thumbnail(url="https://i.imgur.com/EDy6jCp.png")

        await ctx.channel.purge(limit=amount, bulk=True, before=ctx.created_at)
        await ctx.followup.send(embed=embed)
        await log_embed_to_channel(ctx=ctx, embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PurgeCog(bot))
