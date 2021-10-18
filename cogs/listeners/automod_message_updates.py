import logging

from discord import Message
from discord.ext import commands
from utils import automod, embeds
from utils.config import config

log = logging.getLogger(__name__)


class AutomodMessageUpdates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        """Event Listener which is called when a Message is created and sent.
        Parameters:
            message (Message): A Message of the current message.
        Warning:
            Your bot’s own messages and private messages are sent through this event.
        Note:
            This requires Intents.messages to be enabled.
        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_message
        """
        # Ignore messages from all bots (this includes itself).
        if message.author.bot:
            return

        if await automod.check_message(message):
            await message.delete()
            return

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        """Event Listener which is called when a message is edited.
        Note:
            This requires Intents.messages to be enabled.
        Parameters:
            before (Message): The previous version of the message.
            after (Message): The current version of the message.
        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_message_edit
        """
        if after.author.bot:
            # Ignore bots
            return
        if before.clean_content == after.clean_content:
            # Links that have embeds, such as picture URL's are considered edits and need to be ignored.
            return
        # Act as if its a new message rather than an a edit.
        await self.on_message(after)

    @staticmethod
    async def log_automodded_message(message: Message, automod_reason: str):
        embed = embeds.make_embed(
            ctx=None, title="Message removed by automod.", color="red", author=True
        )
        embed.set_author(name=message.author, icon_url=message.author.avatar_url)
        message_content = message.clean_content[0:256]
        removal_reason = automod_reason[0:512]
        if len(automod_reason) > 512:
            removal_reason += "..."
        if len(message.clean_content) > 256:
            message_content += "..."
        embed.description = f"""**Message deleted: ** {message_content}
        **Channel: ** {message.channel.mention}
        **Reason: ** {removal_reason}
        """

        # bot: commands.Bot = self.bot
        automod_log = message.guild.get_channel(config["channels"]["automod_log"])

        await automod_log.send(embed=embed)


def setup(bot: commands.Bot) -> None:
    """Load the message_updates cog."""
    bot.add_cog(AutomodMessageUpdates(bot))
    log.info("Listener loaded: automod_message_updates")
