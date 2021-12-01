import logging
import re

from discord import Message, RawBulkMessageDeleteEvent, RawMessageUpdateEvent
from discord.ext import commands


log = logging.getLogger(__name__)


class MessageUpdates(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: Message):
        """Event Listener which is called when a message is deleted.
        Args:
            message (Message): The deleted message.
        Note:
            This requires Intents.messages to be enabled.
        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_message_delete
        """
        if message.author.bot:
            return
        if message.embeds:
            log.info(f"{message.author} was deleted: {message.embeds}")
        else:
            log.info(f"{message.author} was deleted: {message.clean_content}")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawBulkMessageDeleteEvent):
        """Event Listener which is called when a message is deleted.
        Args:
            payload (RawBulkMessageDeleteEvent): The raw event payload data.
        Note:
            This requires Intents.messages to be enabled.
        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_raw_message_delete
        """

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list):
        """Event Listener which is called when messages are bulk deleted.
        Args:
            messages (list): The messages that have been deleted.
        Note:
            This requires Intents.messages to be enabled.
        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_bulk_message_delete
        """

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        """Event Listener which is called when a bulk delete is triggered.
        Args:
            payload (RawBulkMessageDeleteEvent): The raw event payload data.
        Note:
            This requires Intents.messages to be enabled.
        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html#discord.on_raw_bulk_message_delete
        """

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

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        """Event Listener which is called when a message is edited.
        Note:
            This requires Intents.messages to be enabled.
        Parameters:
            payload (RawMessageUpdateEvent): The raw event payload data.
        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.on_raw_message_edit
        """

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Event Listener which is called when a reaction is added.
        Args:
            reaction (Reaction) – The current state of the reaction.
            user (Union[Member, User]) – The user who added the reaction.
        Note:
            This requires Intents.reactions to be enabled.
        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html?highlight=on_reaction_add#discord.on_reaction_add
        """

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

        # Remove messages containing Cyrillic characters used for bypassing automod.
        if bool(re.search('[\u0400-\u04FF]', message.clean_content)):
            await message.delete()

        # Premptively ban any users who @everyone with "nitro" in their message.
        if all(match in message.content for match in ["nitro", "@everyone"]):
            await message.guild.ban(
                user=message.author,
                reason="Banned by potential Nitro scam link detection",
                delete_message_days=1
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Event Listener which is called when a reaction is added.
        Args:
            payload (RawReactionActionEvent) – The raw event payload data.
        Note:
            This requires Intents.reactions to be enabled.
        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html?highlight=on_reaction_add#discord.on_raw_reaction_add
        """
        # Ignore reactions added by the bot.
        if payload.user_id == self.bot.user.id:
            return


def setup(bot: commands.Bot) -> None:
    """Load the message_updates cog."""
    bot.add_cog(MessageUpdates(bot))
    log.info("Listener loaded: message_updates")
