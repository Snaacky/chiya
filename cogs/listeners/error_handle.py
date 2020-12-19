import logging
import typing as t

from discord.ext.commands import Cog, Context, errors
import discord

from utils import embeds
from utils.record import record_usage


# Enabling logs
log = logging.getLogger(__name__)


"""
    Note, the import is diffrent from regular cogs because of the heavy-useage of:
    commands.Cog, commands.context, and commands.errors
"""


class error_handle(Cog):
    """error_handle"""

    def __init__(self, bot):
        self.bot = bot

    def _get_error_embed(self, title: str, body: str) -> discord.Embed:
        """Return an embed that contains the exception."""
        return discord.Embed(
            title=title,
            color=discord.Color.dark_red,
            description=body
        )

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: errors.CommandError) -> None:
        """
        Provides generic command error handling.
        """

        command = ctx.command

        # Checking if error hasn't already been handled locally
        if hasattr(error, "handled"):
            log.trace(f"Command {command} had its error already handled locally; ignoring.")
            return

        # Going through diffrent types of errors to handle them differently.
        if isinstance(error, errors.CommandNotFound) and not hasattr(ctx, "invoked_from_error_handler"):
            await embeds.error_message(ctx, description=f"Sorry, **`{ctx.invoked_with}`** cannot be located, be sure you typed it correctly.\n\n  ```{error}```")
            log.debug(f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}", exc_info=error)

        elif isinstance(error, errors.UserInputError):
            await self.handle_user_input_error(ctx, error)

        elif isinstance(error, errors.CheckFailure):
            await self.handle_check_failure(ctx, error)

        elif isinstance(error, errors.CommandOnCooldown):
            await ctx.send(error)

        elif not isinstance(error, errors.DisabledCommand):
            # ConversionError, MaxConcurrencyReached, ExtensionError
            await embeds.error_message(ctx, 
            description=f"Sorry, an unexpected error occurred. Please let us know!\n\n" + \
                        f"```{error.__class__.__name__}: {error}```")
            log.error(f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}", exc_info=error)


    async def handle_user_input_error(self, ctx: Context, e: errors.UserInputError) -> None:
        """
        Send an error message in `ctx` for UserInputError, sometimes invoking the help command too.
        * MissingRequiredArgument: send an error message with arg name and the help command
        * TooManyArguments: send an error message and the help command
        * BadArgument: send an error message and the help command
        * BadUnionArgument: send an error message including the error produced by the last converter
        * ArgumentParsingError: send an error message
        * Other: send an error message and the help command
        """

        if isinstance(e, errors.MissingRequiredArgument):
            embed = self._get_error_embed("Missing required argument", e.param.name)
            await ctx.send(embed=embed)
            self.bot.stats.incr("errors.missing_required_argument")

        elif isinstance(e, errors.TooManyArguments):
            embed = self._get_error_embed("Too many arguments", str(e))
            await ctx.send(embed=embed)
            self.bot.stats.incr("errors.too_many_arguments")

        elif isinstance(e, errors.BadArgument):
            embed = self._get_error_embed("Bad argument", str(e))
            await ctx.send(embed=embed)
            self.bot.stats.incr("errors.bad_argument")

        elif isinstance(e, errors.BadUnionArgument):
            embed = self._get_error_embed("Bad argument", f"{e}\n{e.errors[-1]}")
            await ctx.send(embed=embed)
            self.bot.stats.incr("errors.bad_union_argument")

        elif isinstance(e, errors.ArgumentParsingError):
            embed = self._get_error_embed("Argument parsing error", str(e))
            await ctx.send(embed=embed)
            self.bot.stats.incr("errors.argument_parsing_error")

        else:
            embed = self._get_error_embed(
                "Input error",
                "Something about your input seems off. Check the arguments and try again."
            )
            await ctx.send(embed=embed)
            self.bot.stats.incr("errors.other_user_input_error")

    # Handle errors with permissions.
    @staticmethod
    async def handle_check_failure(ctx: Context, error: errors.CheckFailure) -> None:
        """
        Send an error message in `ctx` for certain types of CheckFailure.
        The following types are handled:
        * BotMissingPermissions
        * BotMissingRole
        * BotMissingAnyRole
        * NoPrivateMessage
        * InWhitelistCheckFailure
        """
        bot_missing_errors = (
            errors.BotMissingPermissions,
            errors.BotMissingRole,
            errors.BotMissingAnyRole
        )

        if isinstance(error, bot_missing_errors):
            ctx.bot.stats.incr("errors.bot_permission_error")
            await ctx.send(
                "Sorry, it looks like I don't have the permissions or roles I need to do that."
            )
        elif isinstance(error, (errors.NoPrivateMessage)):
            ctx.bot.stats.incr("errors.wrong_channel_or_dm_error")
            await ctx.send(error)

    # General HTTP error handle
    @staticmethod
    async def handle_api_error(ctx: Context, error) -> None:
        """Send an error message in `ctx` and log it."""
        if error.status == 404:
            await ctx.send("There does not seem to be anything matching your query.")
            log.debug(f"API responded with 404 for command {ctx.command}")
            ctx.bot.stats.incr("errors.api_error_404")
        elif error.status == 400:
            content = await error.response.json()
            log.debug(f"API responded with 400 for command {ctx.command}: %r.", content)
            await ctx.send("According to the API, your request is malformed.")
            ctx.bot.stats.incr("errors.api_error_400")
        elif 500 <= error.status < 600:
            await ctx.send("Sorry, there seems to be an internal issue with the API.")
            log.warning(f"API responded with {error.status} for command {ctx.command}")
            ctx.bot.stats.incr("errors.api_internal_server_error")
        else:
            await ctx.send(f"Got an unexpected status code from the API (`{error.status}`).")
            log.warning(f"Unexpected API response for command {ctx.command}: {error.status}")
            ctx.bot.stats.incr(f"errors.api_error_{error.status}")


def setup(bot) -> None:
    """Load the error_handle cog."""
    bot.add_cog(error_handle(bot))
    log.info("Cog loaded: error_handle")
