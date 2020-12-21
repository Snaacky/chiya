import logging

import discord
from discord.ext.commands import Cog, Context, errors

from utils import embeds
#from utils.record import record_usage


# Enabling logs
log = logging.getLogger(__name__)


"""
    Note, the import is diffrent from regular cogs because of the heavy-useage of:
    commands.Cog, commands.context, and commands.errors
"""


class error_handle(Cog):
    """error_handle."""

    def __init__(self, bot):
        self.bot = bot

    def _get_error_embed(self, ctx: Context, title: str, body: str) -> discord.Embed:
        """Return an embed that contains the exception."""
        log.trace(f"{title}, {body}")
        return embeds.error_embed(ctx, title=title, description=body)

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: errors.CommandError) -> None:
        """Provides generic command error handling."""

        command = ctx.command

        # Checking if error hasn't already been handled locally
        if hasattr(error, "handled"):
            log.trace(
                f"Command {command} had its error already handled locally; ignoring."
            )
            return

        # Going through diffrent types of errors to handle them differently.
        if isinstance(error, errors.CommandNotFound) and not hasattr(
            ctx, "invoked_from_error_handler"
        ):
            await embeds.error_message(
                ctx,
                description=f"Sorry, **`{ctx.invoked_with}`** cannot be located, be sure you typed it correctly.\n\n  ```{error}```",
            )
            log.debug(
                f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}",
                exc_info=error,
            )

        elif isinstance(error, errors.UserInputError):
            await self.handle_user_input_error(ctx, error)

        elif isinstance(error, errors.CheckFailure):
            await self.handle_check_failure(ctx, error)

        elif isinstance(error, errors.CommandOnCooldown):
            await ctx.send(error)

        elif not isinstance(error, errors.DisabledCommand):
            # ConversionError, MaxConcurrencyReached, ExtensionError
            await embeds.error_message(
                ctx,
                description=f"Sorry, an unexpected error occurred. Please let us know!\n\n"
                + f"```{error.__class__.__name__}: {error}```",
            )
            log.error(
                f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}",
                exc_info=error,
            )
        else:
            await embeds.error_message(
                ctx,
                description=f"Sorry, an unexpected error occurred. Please let us know!\n\n"
                + f"```{error.__class__.__name__}: {error}```",
            )
            log.error(
                f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}",
                exc_info=error,
            )
    async def handle_user_input_error(
        self, ctx: Context, error: errors.UserInputError
    ) -> None:
        """### Send an error message in `ctx` for UserInputError, sometimes
        invoking the help command too. \n.

        - MissingRequiredArgument: send an error message with arg name \n
        - TooManyArguments: send an error message \n
        - BadArgument: send an error message \nr message with arg name \n
        - TooManyArguments: send an error message \n
        - BadArgument: send an error message \n
        - BadUnionArgument: send an error message including the error produced by the last converter \n
        - ArgumentParsingError: send an error message \n
        - Other: send an error message \n
        """

        if isinstance(error, errors.MissingRequiredArgument):
            # TODO: Display correct syntax of command
            embed = self._get_error_embed(
                ctx, "Missing required argument", error.param.name
            )
            await ctx.send(embed=embed)

        elif isinstance(error, errors.TooManyArguments):
            # TODO: Display correct syntax of command
            embed = self._get_error_embed(ctx, "Too many arguments", str(error))
            await ctx.send(embed=embed)

        elif isinstance(error, errors.BadArgument):
            # TODO: Display correct syntax of command
            embed = self._get_error_embed(ctx, "Bad argument", str(error))
            await ctx.send(embed=embed)

        elif isinstance(error, errors.BadUnionArgument):
            # TODO: Display correct syntax of command
            embed = self._get_error_embed(ctx, "Bad argument", f"{error}\n{error.errors[-1]}")
            await ctx.send(embed=embed)

        elif isinstance(error, errors.ArgumentParsingError):
            # TODO: Display correct syntax of command
            embed = self._get_error_embed(ctx, "Argument parsing error", str(error))
            await ctx.send(embed=embed)

        else:
            embed = self._get_error_embed(
                ctx,
                "Input error",
                "Something about your input seems off. Check the arguments and try again.",
            )

    # Handle errors with deal with user or bot permissions.
    async def handle_check_failure(self, ctx: Context, error: errors.CheckFailure) -> None:
        """### Send an error message in `ctx` for certain types of
        CheckFailure. The following types are handled:

        - BotMissingPermissions
        - BotMissingRole
        - BotMissingAnyRole
        - BotMissingAnyRole
        - NoPrivateMessage
        """
        bot_missing_errors = (
            errors.BotMissingPermissions,
            errors.BotMissingRole,
            errors.BotMissingAnyRole,
        )

        if isinstance(error, bot_missing_errors):
            embed = self._get_error_embed(
                ctx, "Missing required permissions or roles", error.param.name
            )
            try:
                await ctx.send(embed=embed)
            except: # this will likely fail if the error to begin with is not able to post embeds
                await ctx.send(
                    "Sorry, it looks like I don't have the permissions or roles I need to do that.\n" +
                        f"Missing: `{error.param.name}`"
                )

        elif isinstance(error, (errors.NoPrivateMessage)):
            await ctx.send(error)

    # General HTTP error handle
    @staticmethod
    async def handle_api_error(ctx: Context, error) -> None:
        """Send an error message in `ctx` and log it."""
        if error.status == 404:
            await ctx.send("There does not seem to be anything matching your query.")
            log.debug(f"API responded with 404 for command {ctx.command}")

        elif error.status == 400:
            await ctx.send("According to the API, your request is malformed.")
            content = await error.response.json()
            log.debug(f"API responded with 400 for command {ctx.command}: %r.", content)    

        elif 500 <= error.status < 600:
            await ctx.send("Sorry, there seems to be an internal issue with the API.")
            log.warning(f"API responded with {error.status} for command {ctx.command}")

        else:
            await ctx.send(
                f"Got an unexpected status code from the API (`{error.status}`)."
            )
            log.warning(
                f"Unexpected API response for command {ctx.command}: {error.status}"
            )


def setup(bot) -> None:
    """Load the error_handle cog."""
    bot.add_cog(error_handle(bot))
    log.info("Cog loaded: error_handle")
