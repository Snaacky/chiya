import logging

import discord
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext
from discord_slash.context import MenuContext
from discord_slash.model import ContextMenuType

from utils.config import config
from utils import embeds


log = logging.getLogger(__name__)


class MoveQuestionCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_context_menu(
        target=ContextMenuType.MESSAGE,
        name="Move question",
        guild_ids=[config["guild_id"]]
    )
    async def move_question(self, ctx: MenuContext):
        """
        Context menu command for moving questions (messages) to #questions-and-help.

        Args:
            ctx (MenuContext): The context of the context menu.

        TODO:
            Fix "Deferred response might not be what you set it to!" warning.
        """
        await ctx.defer(hidden=True)

        staff = [x for x in ctx.author.roles
                 if x.id == config["roles"]["staff"]
                 or x.id == config["roles"]["trial_mod"]]
        if not staff:
            return await embeds.error_message(ctx=ctx, description="You do not have permissions to use this command.")

        if ctx.channel.category_id in [
                config["categories"]["moderation"],
                config["categories"]["development"],
                config["categories"]["logs"],
                config["categories"]["tickets"]]:
            return await embeds.error_message(
                ctx=ctx,
                description="You do not have permissions to use this command in this category."
            )

        channel = discord.utils.get(ctx.guild.text_channels, id=config["channels"]["questions_and_help"])
        webhook = await channel.create_webhook(name=ctx.target_message.author)

        await webhook.send(
            str(ctx.target_message.clean_content),
            username=ctx.target_message.author.name,
            avatar_url=ctx.target_message.author.avatar_url
        )
        await webhook.delete()
        await ctx.target_message.delete()

        await embeds.success_message(ctx=ctx, description=f"Successfully moved message to: {channel.mention}")
        await embeds.warning_message(
            ctx=ctx,
            title="Warning: Your question was moved",
            description=(
                f"{ctx.target_message.author.mention}, your message was moved to {channel.mention} "
                "which is the more appropriate channel for help, questions, and support type "
                "topics. Please continue your conversation in that channel."
            ),
            author=False
        )
        ping = await channel.send(ctx.target_message.author.mention)
        await ping.delete()


def setup(bot: Bot) -> None:
    bot.add_cog(MoveQuestionCog(bot))
    log.info("App loaded: move_question")
