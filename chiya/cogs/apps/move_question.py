import logging
from subprocess import call

import aiohttp
import discord
from discord import app_commands, Webhook
from discord.ext import commands
from discord.ext.commands import Cog

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class MoveQuestionApp(Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.move_question_command = app_commands.ContextMenu(name="Move Question", callback=self.move_question)
        self.bot.tree.add_command(self.move_question_command)

    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    async def move_question(self, ctx: discord.Interaction, message: discord.Message):
        await ctx.response.defer(thinking=True, ephemeral=True)

        staff = [x for x in ctx.user.roles if x.id == config["roles"]["staff"] or x.id == config["roles"]["trial"]]
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
        await ctx.followup.send(embed=success_embed)

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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MoveQuestionApp(bot))
    log.info("App loaded: move_question")
