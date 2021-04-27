import logging
import itertools
from typing import List, Union

from discord import Embed
from discord.ext.commands import Bot, Cog, Command, Group, HelpCommand, CommandError
from utils import embeds
from utils.pagination import LinePaginator
import config

# Enabling logs.
log = logging.getLogger(__name__)

COMMANDS_PER_PAGE = 7
PREFIX = config.prefix
TIME_TO_LIVE = 120 # In seconds, how long an embed should remain until self-destruct.

class CustomHelpCommand(HelpCommand):
    """CustomHelpCommand"""

    def __init__(self):
        # Info about the help command.
        super().__init__(command_attrs={"help": "Shows help for bot commands"})

    @staticmethod
    def _category_key(command: Command) -> str:
        """Returns the cog's name of a given command to use as a key.

        A zero width space is used as a prefix for results with no cogs to force them last in ordering.

        Args:
            command (Command): The command object

        Returns:
            str: Cog's name or "No Category" if name doesn't exist
        """

        if command.cog:
            try:
                return f"**{command.cog.category}**"
            except AttributeError:
                return f"**{command.cog_name}**"
        else:
            return "**\u200bNo Category:**"

    @staticmethod
    def get_commands_brief_details(commands: List[Command], return_as_list: bool = False) -> Union[List[str], str]:
        """Iterates through the list of commands and returns a formated string of the command's useage and documentation

        Example:
            '\\n**`-help [command]`**\\n*Shows help for bot commands*'

        Args:
            commands (List[Command]): List of commands
            return_as_list (bool, optional): for passing these command details into the paginator as a
                list of command details. Defaults to False.

        Returns:
            Union[List[str], str]: returns list or str depending on `return_as_list`
        """

        details = []

        for command in commands:
            signature = f" {command.signature}" if command.signature else ""
            details.append(f"\n**`{PREFIX}{command.qualified_name}{signature}`**\n*")

            if command.help is None:
                details.append("No details provided*")
            else:
                details.append(f"{command.short_doc.strip()}*")

        if return_as_list:
            return details
        return "".join(details)

    async def command_formatting(self, command: Command) -> Embed:
        """Takes a command and turns it into an embed.
        It will add an author, command signature + help, aliases and a note if the user can't run the command.

        Args:
            command (Command): Command to be formatted.

        Returns:
            Embed: Embed object of the formatted command.
        """

        embed = embeds.make_embed(
            title="Command Help",
            image_url="https://cdn.discordapp.com/emojis/512367613339369475.png",
            context=self.context
            )

        # Retrieves the fully qualified parent command name.
        # For example, in `?one two three` the parent name would be `one two`.
        parent = command.full_parent_name

        name = str(command) if not parent else f"{parent} {command.name}"
        command_details = f"**```{PREFIX}{name} {command.signature}```**\n"

        # Show command's aliases.
        aliases = [f"`{alias}`" if not parent else f"`{parent} {alias}`" for alias in command.aliases]
        aliases += [f"`{alias}`" for alias in getattr(command, "root_aliases", ())]
        aliases = ", ".join(sorted(aliases))
        if aliases:
            command_details += f"**Can also use:** {aliases}\n\n"

        # Check if the user is allowed to run the command, such as is_owner() or disabled.
        # If can_run() is false, then it raises an excepion, in this case, we do not want that.
        try:
            await command.can_run(self.context)
        except CommandError:
            command_details += "***You cannot run this command.***\n\n"


        if command.help is None:
            command_details += "*No details provided.*\n"
        else:
            command_details += f"*{command.help.strip()}*\n"

        embed.description = command_details

        return embed

    async def send_bot_help (self, mapping: dict) -> None:
        """ Handles the implementation of the bot command page in the help command.
        This function is called when the help command is called with no arguments.

        Args:
            mapping (dict): A mapping of cogs to commands that have been requested by the user for help.
                The key of the mapping is the Cog that the command belongs to, or None if there isn’t one,
                and the value is a list of commands that belongs to that cog.

        note:
            You can access the invocation context with `HelpCommand.context`.

        For more info:
            https://discordpy.readthedocs.io/en/stable/ext/commands/api.html?#discord.ext.commands.HelpCommand.send_bot_help
            Due note, the docs are not clear on this...
        """
        bot = self.context.bot

        # If the user can't use it, then it doesn't show. such as IsOwner().
        filtered_commands = await self.filter_commands(bot.commands, sort=True, key=self._category_key)

        cog_or_category_pages = []

        # Grouping commands together based on cog or category.
        for cog_or_category, _commands in itertools.groupby(filtered_commands, key=self._category_key):
            sorted_commands = sorted(_commands, key=lambda c: c.name)

            if len(sorted_commands) == 0:
                continue

            # Get each command's info from the cog/category.
            command_detail_lines = self.get_commands_brief_details(sorted_commands, return_as_list=True)

            # Split cogs or categories which have too many commands to fit in one page.
            # The length of commands is included for later use when aggregating into pages for the paginator.
            for index in range(0, len(sorted_commands), COMMANDS_PER_PAGE*2):
                truncated_lines = command_detail_lines[index:index + COMMANDS_PER_PAGE*2]
                joined_lines = "".join(truncated_lines)
                cog_or_category_pages.append((f"**{cog_or_category}**{joined_lines}", len(truncated_lines)))

        pages = []
        counter = 0
        page = ""
        for page_details, length in cog_or_category_pages:
            counter += length
            if counter > COMMANDS_PER_PAGE*2:
                # force a new page on paginator even if it falls short of the max pages
                # since we still want to group categories/cogs.
                counter = length
                pages.append(page)
                page = f"{page_details}\n\n"
            else:
                page += f"{page_details}\n\n"

        if page:
            # add any remaining command help that didn't get added in the last iteration above.
            pages.append(page)

        embed = embeds.make_embed(
            title="Command: Help",
            image_url="https://cdn.discordapp.com/emojis/512367613339369475.png",
            context=self.context
            )
        await LinePaginator.paginate(pages, self.context, embed=embed, max_lines=1,
            max_size=2000, restrict_to_user=self.context.author, time_to_delete=TIME_TO_LIVE)


        log.trace(pages)

    async def send_cog_help (self, cog: Cog) -> None:
        """Handles the implementation of the cog page in the help command.
        This function is called when the help command is called with a cog as the argument.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.ext.commands.HelpCommand.send_cog_help

        Args:
            cog (Cog): The cog that was requested for help.
        """
        # Sort commands by name and if the user can't use it, then it doesn't show. Such as IsOwner().
        commands_ = await self.filter_commands(cog.get_commands(), sort=True)

        embed = embeds.make_embed(
            title="Command Help",
            image_url="https://cdn.discordapp.com/emojis/512367613339369475.png",
            context=self.context
            )

        if cog.description is None:
            embed.description = f"**{cog.qualified_name}**\n*No details provided.*"
        else:
            embed.description = f"**{cog.qualified_name}**\n*{cog.description.strip()}*"

        # Append description if there is more info.
        command_details = self.get_commands_brief_details(commands_)
        if command_details:
            embed.description += f"\n\n**Commands:**\n{command_details}"

        await self.context.send(embed=embed, delete_after=TIME_TO_LIVE)

    async def send_group_help (self, group: Group) -> None:
        """Handles the implementation of the group page in the help command.
        This function is called when the help command is called with a group as the argument.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.ext.commands.HelpCommand.send_group_help

        Args:
            group (Group): The group that was requested for help.
        """
        subcommands = group.commands

        if len(subcommands) == 0:
            # No subcommands, just treat it like a regular command.
            await self.send_command_help(group)
            return

        # Remove subcommands that the user can't run or are hidden, and sort by name.
        # Note: Only checks the subcommands themselves for checks, not the root command.
        filtered_commands = await self.filter_commands(subcommands, sort=True)

        embed = await self.command_formatting(group)

        group_pages = []

        for cog_name, _commands in itertools.groupby(filtered_commands, key=self._category_key):
            sorted_commands = sorted(_commands, key=lambda c: c.name)

            if len(sorted_commands) == 0:
                continue

            # Get each command's info in the group.
            command_detail_lines = self.get_commands_brief_details(sorted_commands, return_as_list=True)

            # Split cogs or categories which have too many commands to fit in one page.
            # The length of commands is included for later use when aggregating into pages for the paginator.
            for index in range(0, len(sorted_commands), COMMANDS_PER_PAGE*2):
                truncated_lines = command_detail_lines[index:index + COMMANDS_PER_PAGE*2]
                joined_lines = "".join(truncated_lines)
                group_pages.append((f"{joined_lines}", len(truncated_lines)))

        pages = []
        counter = 0
        page = ""
        for page_details, length in group_pages:
            counter += length
            if counter > COMMANDS_PER_PAGE*2:
                # force a new page on paginator even if it falls short of the max pages
                counter = length
                pages.append(embed.description + page)
                page = f"{page_details}\n\n"
            else:
                page += f"{page_details}\n\n"

        if page:
            # add any remaining command help that didn't get added in the last iteration above.
            pages.append(embed.description + page)

        log.debug("Sending group help to paginator")
        await LinePaginator.paginate(pages, self.context, embed=embed, max_lines=1,
        max_size=2000, restrict_to_user=self.context.author, time_to_delete=TIME_TO_LIVE)

    async def send_command_help (self, command: Command) -> None:
        """Handles the implementation of the single command page in the help command.
        This function is called when the help command is called with a command as the argument.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.ext.commands.HelpCommand.send_command_help

        Args:
            command (Command): The command that was requested for help.
        """
        embed = await self.command_formatting(command)
        await self.context.send(embed=embed, delete_after=TIME_TO_LIVE)

class Help(Cog):
    """Custom Embed Pagination Help feature."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        # Overiding default help command with new custom command.
        self.old_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self) -> None:
        """Reset the help command when the cog is unloaded."""
        self.bot.help_command = self.old_help_command

def setup(bot: Bot) -> None:
    """Load the Help cog."""
    bot.add_cog(Help(bot))
    log.info("Commands loaded: help")
