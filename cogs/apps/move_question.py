import logging

import discord
from discord import message_command
from discord.commands import context
from discord.ext import commands

from utils import embeds
from utils.config import config


log = logging.getLogger(__name__)


class MoveQuestionApp(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @message_command(guild_ids=config["guild_ids"], name="Move Question")
    async def move_question(self, ctx: context.ApplicationContext, message: discord.Message) -> None:
        """
        Context menu command for moving questions (messages) to
        #questions-and-help.
        """
        await ctx.defer(ephemeral=True)

        staff = [x for x in ctx.author.roles if x.id == config["roles"]["staff"] or x.id == config["roles"]["trial"]]
        if not staff:
            return await embeds.error_message(ctx=ctx, description="You do not have permissions to use this command.")

        if ctx.channel.category_id in [
            config["categories"]["moderation"],
            config["categories"]["development"],
            config["categories"]["logs"],
            config["categories"]["tickets"],
        ]:
            return await embeds.error_message(
                ctx=ctx,
                description="You do not have permissions to use this command in this category.",
            )

        channel = discord.utils.get(
            ctx.guild.text_channels,
            id=config["channels"]["public"]["questions_and_help"],
        )
        webhook = await channel.create_webhook(name=ctx.author.name)

        await webhook.send(
            content=message.content,
            username=ctx.author.name,
            avatar_url=ctx.author.avatar,
        )
        await webhook.delete()
        await message.delete()

        await embeds.success_message(ctx=ctx, description=f"Successfully moved message to: {channel.mention}")
        await embeds.warning_message(
            ctx=ctx,
            title="Warning: Your question was moved",
            description=(
                f"{ctx.author.mention}, your message was moved to {channel.mention} "
                "which is the more appropriate channel for help, questions, and support type "
                "topics. Please continue your conversation in that channel."
            ),
        )
        ping = await channel.send(ctx.author.mention)
        await ping.delete()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(MoveQuestionApp(bot))
    log.info("App loaded: move_question")
