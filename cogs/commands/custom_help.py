import logging
import itertools
from typing import List, Union

from discord.ext.commands import Bot, Cog, Command, Group, HelpCommand
from utils import embeds
import config


# Enabling logs
log = logging.getLogger(__name__)

COMMANDS_PER_PAGE = 8
PREFIX = config.PREFIX


class CustomHelpCommand(HelpCommand):
    """CustomHelpCommand"""

    def __init__(self):
        # Info about the help command
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
            details.append(
                f"\n**`{PREFIX}{command.qualified_name}{signature}`**\n*"
                f"{command.short_doc or 'No details provided'}*")
        if return_as_list:
            return details
        return "".join(details)

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

        # If the user can't use it, then it doesn't show. such as IsOwner()
        filtered_commands = await self.filter_commands(bot.commands, sort=True, key=self._category_key)

        cog_or_category_pages = []

        for cog_or_category, _commands in itertools.groupby(filtered_commands, key=self._category_key):
            sorted_commands = sorted(_commands, key=lambda c: c.name)

            if len(sorted_commands) == 0:
                continue

            command_detail_lines = self.get_commands_brief_details(sorted_commands, return_as_list=True)


            # Split cogs or categories which have too many commands to fit in one page.
            # The length of commands is included for later use when aggregating into pages for the paginator.
            for index in range(0, len(sorted_commands), COMMANDS_PER_PAGE):
                truncated_lines = command_detail_lines[index:index + COMMANDS_PER_PAGE]
                joined_lines = "".join(truncated_lines)
                cog_or_category_pages.append((f"**{cog_or_category}**{joined_lines}", len(truncated_lines)))

        pages = []
        counter = 0
        page = ""
        for page_details, length in cog_or_category_pages:
            counter += length
            if counter > COMMANDS_PER_PAGE:
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
            description=pages[0],
            image_url="https://cdn.discordapp.com/emojis/512367613339369475.png"
            )
        #embed.add_field(name="test", value=pages[0])
        await self.context.send(embed=embed)
        log.info(pages)

    async def send_cog_help (self, cog: Cog) -> None:
        """Handles the implementation of the cog page in the help command.
        This function is called when the help command is called with a cog as the argument.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.ext.commands.HelpCommand.send_cog_help

        Args:
            cog (Cog): The cog that was requested for help.
        """
        # TODO: Write this function.

    async def send_group_help (self, group: Group) -> None:
        """Handles the implementation of the group page in the help command.
        This function is called when the help command is called with a group as the argument.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.ext.commands.HelpCommand.send_group_help

        Args:
            group (Group): The group that was requested for help.
        """
        # TODO: Write this function.

    async def send_command_help (self, command: Command) -> None:
        """Handles the implementation of the single command page in the help command.
        This function is called when the help command is called with a command as the argument.

        For more information:
            https://discordpy.readthedocs.io/en/stable/api.html#discord.ext.commands.HelpCommand.send_command_help

        Args:
            command (Command): The command that was requested for help.
        """
        # TODO: Write this function.

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
    log.info("Cog loaded: Help")
