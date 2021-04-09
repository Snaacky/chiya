import logging

import discord
from discord import Message, RawBulkMessageDeleteEvent, RawMessageUpdateEvent
from discord.ext import commands

import config
from utils import embeds
from utils.utils import contains_link, has_attachment

log = logging.getLogger(__name__)

class MessageUpdates(commands.Cog):
    """Message event handler cog."""

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

        # If message does not follow with the above code, treat it as a potential command.
        await self.bot.process_commands(message)
        
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
    async def on_raw_reaction_add(self, payload):
        """Event Listener which is called when a reaction is added.

        Args:
            payload (RawReactionActionEvent) – The raw event payload data.

        Note:
            This requires Intents.reactions to be enabled.

        For more information:
            https://discordpy.readthedocs.io/en/latest/api.html?highlight=on_reaction_add#discord.on_raw_reaction_add
        """
        # Ignore all reactions that are not for the ticket system.
        if payload.message_id != config.ticket_embed_id:
            return
        
        # Get the member object for the user who added the reaction.
        member = payload.member.guild.get_member(payload.member.id)

        # Remove the users reaction to the creation embed.
        channel = discord.utils.get(payload.member.guild.channels, id=config.ticket_channel)
        embed = await channel.fetch_message(config.ticket_embed_id)
        logging.info(f"{embed} | {type(embed)}")
        await embed.remove_reaction("🎫", member)

        # Check if the user already has a ticket open.  
        results = discord.utils.get(discord.utils.get(payload.member.guild.categories, 
                                    id=config.ticket_category_id).text_channels, 
                                    name=f"ticket-{payload.user_id}")

        # The user already had a ticket open so send them a DM warning with a link to the existing ticket.
        if results:
            logging.info(f"{member} tried to create a new ticket but already had one open: {results}")
            try:
                # Try/catch is required because some users don't accept DMs from mutual server members.
                dm = await member.create_dm()
                embed = embeds.make_embed(author=False, color=0xf999de)
                embed.title = f"Uh-oh, an error occurred!"
                embed.description = f"You attempted to create a new ticket but you already have one open. Please refer to {results.mention} for assistance."
                embed.set_image(url="https://i.imgur.com/VTqz1oS.gif")
                await dm.send(embed=embed)
            except discord.errors.Forbidden:
                # Could not DM the user because they don't accept DMs from mutual server members.
                logging.info(f"{member} tried to create a new ticket but already had one open: {results} and is not accepting DMs.")
                pass
            return

        # Create a channel in the desired tickets category according to the config.
        category = discord.utils.get(payload.member.guild.categories, id=config.ticket_category_id)        
        ticket = await payload.member.guild.create_text_channel(f"ticket-{payload.member.id}", category=category)

        # Give both the staff and the user perms to access the channel. 
        await ticket.set_permissions(discord.utils.get(payload.member.guild.roles, id=config.role_trial_mod), read_messages=True)
        await ticket.set_permissions(discord.utils.get(payload.member.guild.roles, id=config.role_staff), read_messages=True)
        await ticket.set_permissions(member, read_messages=True)

        embed = embeds.make_embed(title="🎫  Ticket created", 
                                  description="Please remain patient for a staff member to assist you.", 
                                  color="default")
        embed.add_field(name="Ticket Creator:", value=member.mention)
        await ticket.send(embed=embed)

        logging.info(f"{member} created a new modmail ticket: {ticket.id}")

        # Alert staff and the user to the new modmail ticket channel created.
        await ticket.send("@here")
        


def setup(bot: commands.Bot) -> None:
    """Load the message_updates cog."""
    bot.add_cog(MessageUpdates(bot))
    log.info("Cog loaded: message_updates")
