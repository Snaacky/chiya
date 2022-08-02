import logging

import aiohttp
import discord
from discord import message_command, Webhook
from discord.commands import context
from discord.ext import commands

from chiya import config
from chiya.utils import embeds


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

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(
                url=config["bot"]["webhook_url"],
                session=session,
            )

            content = f"{message.content}\n\n"
            for attachment in message.attachments:
                content += f"{attachment.url}\n"

            await webhook.send(
                content=content,
                username=message.author.name,
                avatar_url=message.author.avatar,
            )

        success_embed = embeds.make_embed(
            description=f"Successfully moved message to: {channel.mention}",
            color=discord.Color.green(),
        )
        await ctx.send_followup(embed=success_embed)
        await embeds.warning_message(
            ctx=ctx,
            title="Warning: Your question was moved",
            description=(
                f"{message.author.mention}, your message was moved to {channel.mention} "
                "which is the more appropriate channel for help, questions, and support type "
                "topics. Please continue your conversation in that channel."
            ),
        )
        ping = await channel.send(message.author.mention)
        await ping.delete()
        await message.delete()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(MoveQuestionApp(bot))
    log.info("App loaded: move_question")
