import logging
from typing import Optional

import aiohttp
import discord
from discord.ext.commands import Cog, Context, errors

from utils import embeds

# Enabling logs
log = logging.getLogger(__name__)


"""
    Note, the import is diffrent from regular cogs because of the heavy-useage of:
    commands.Cog, commands.context, and commands.errors
"""

# The time, in seconds, for a message to be displayed
AUTO_DELETE_TIME=30

class error_handle(Cog):
    """error_handle."""

    def __init__(self, bot):
        self.bot = bot

    def _get_error_embed(self, title: str, body: str, ctx: Context) -> discord.Embed:
        """Return an embed that contains the exception.

        Args:
            title (str): Name of error.
            body (str): Error message.
            ctx (Context): Discord context object, needed for author and timestamps.

        Returns:
            discord.Embed: discord embed object.
        """
        log.trace(f"{title}, {body}")
        embed = embeds.error_embed(title=title, description=body, ctx=ctx)
        embed.set_footer(
            text=f"This message will self-destruct in {AUTO_DELETE_TIME} seconds.",
            icon_url="https://cdn.discordapp.com/emojis/477907608057937930.png")
        return embed

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: errors.CommandError) -> None:
        """An error handler that is called when an error is raised inside a command either
        through user input error, check failure, or an error in your own code.

        Handled errors:
            CommandNotFound
            UserInputError
            CheckFailure
            CommandOnCooldown
            DisabledCommand


        CommandInvokeError
        MaxConcurrencyReached

        For more information:
            https://discordpy.readthedocs.io/en/stable/ext/commands/api.html?highlight=on_command_error#discord.on_command_error

        Args:
            ctx (Context): The invocation context.
            error (errors.CommandError): The error that was raised.
        """

        command = ctx.command

        # Checking if error hasn't already been handled locally
        if hasattr(error, "handled"):
            log.trace(f"Command {command} had its error already handled locally; ignoring.")
            return

        # Going through diffrent types of errors to handle them differently.
        if isinstance(error, errors.CommandNotFound) and not hasattr(ctx, "invoked_from_error_handler"):
            return

        elif isinstance(error, errors.UserInputError):
            await self.handle_user_input_error(ctx, error)

        elif isinstance(error, errors.CheckFailure):
            await self.handle_check_failure(ctx, error)

        elif isinstance(error, errors.CommandOnCooldown):
            await ctx.send(
                embed=self._get_error_embed(
                    title="Command On Cooldown",
                    body=error,
                    ctx=ctx
                ),
                delete_after=AUTO_DELETE_TIME
            )

        elif isinstance(error, errors.DisabledCommand):
            await ctx.send(
                embed=self._get_error_embed(
                    title="Error",
                    body="Command Disabled",
                    ctx=ctx
                ),
                delete_after=AUTO_DELETE_TIME
            )

            log.debug("test")

        elif isinstance(error, errors.MaxConcurrencyReached):
            await ctx.send(
                embed=self._get_error_embed(
                    title="Error",
                    body="max simultaneous users for command reached",
                    ctx=ctx
                ),
                delete_after=AUTO_DELETE_TIME
            )

        elif isinstance(error, errors.CommandInvokeError):
            # Raised when the command being invoked raised an custom exception.
            if isinstance(error.original, ResponseCodeError):
                await self.handle_api_error(ctx, error.original)

            await self.handle_unexpected_error(ctx, error)
        else:
            await self.handle_unexpected_error(ctx, error)

    async def handle_user_input_error(
        self, ctx: Context, error: errors.UserInputError
    ) -> None:
        """Send an error message embed for UserInputError.

        Handled errors:
            MissingRequiredArgument
            TooManyArguments
            BadArgument
            BadUnionArgument
            ArgumentParsingError

        Args:
            ctx (Context): Discord context object, needed for author and timestamps.
            error (errors.CheckFailure): The error that was raised.
        """
        if isinstance(error, errors.MissingRequiredArgument):
            embed = self._get_error_embed(
                title="Missing required argument",
                body=error.param.name,
                ctx=ctx
            )
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)

        elif isinstance(error, errors.TooManyArguments):
            embed = self._get_error_embed(
                title="Too many arguments",
                body=str(error),
                ctx=ctx
                )
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)

        elif isinstance(error, errors.BadArgument):
            embed = self._get_error_embed(
                title="Bad argument",
                body=str(error),
                ctx=ctx)
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)

        elif isinstance(error, errors.BadUnionArgument):
            embed = self._get_error_embed(
                title="Bad argument",
                body=f"{error}\n{error.errors[-1]}",
                ctx=ctx)
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)

        elif isinstance(error, errors.ArgumentParsingError):
            embed = self._get_error_embed(
                title="Argument parsing error",
                body=str(error),
                ctx=ctx)
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)

        else:
            await self.handle_unexpected_error(ctx, error)
        # Display correct syntax of command.
        # await ctx.send_help(ctx.command)

    # Handle errors with deal with user or bot permissions.
    async def handle_check_failure(self, ctx: Context, error: errors.CheckFailure) -> None:
        """Send an error message embed for certain types of CheckFailure.

        Handled errors:
            Bot missing errors:
                BotMissingPermissions
                BotMissingRole
                BotMissingAnyRole
            User missing errors:
                MissingPermission
                MissingRole
                MissingAnyRole
            Check Errors:
                CheckFailure
                CheckAnyFailure
            NotOwner
            NoPrivateMessage
            PrivateMessageOnly
            NSFWChannelRequired

        Args:
            ctx (Context): Discord context object, needed for author and timestamps.
            error (errors.CheckFailure): The error that was raised.
        """

        bot_missing_errors = (
            errors.BotMissingPermissions,
            errors.BotMissingRole,
            errors.BotMissingAnyRole,
        )

        user_missing_errors = (
            errors.MissingPermissions,
            errors.MissingRole,
            errors.MissingAnyRole,
        )

        check_errors = (
            errors.CheckAnyFailure,
            errors.CheckFailure
        )

        if isinstance(error, bot_missing_errors):
            embed = self._get_error_embed(
                title="Bot is missing required permissions or roles",
                body=f"Missing: `{error.args[0]}`",
                ctx=ctx
            )
            try:
                await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)
            except: # this will likely fail if the error to begin with is not able to post embeds
                await ctx.send(
                    "Sorry, it looks like I don't have the permissions or roles I need to do that.\n" +
                        f"Missing: `{error.args[0]}`",
                    delete_after=AUTO_DELETE_TIME
                )
            log.info(f"Bot missing permissions {error.args[0]=} in {ctx.guild.name=}")

        elif isinstance(error, user_missing_errors):
            embed = self._get_error_embed(
                title="You are missing required permissions or roles",
                body=f"Missing: `{error.args[0]}`",
                ctx=ctx
            )
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)
            log.debug(f"{ctx.author} missing permissions {error.args[0]=} in {ctx.guild.name=}")

        elif isinstance(error, user_missing_errors):
            embed = self._get_error_embed(
                title="Check Failed",
                body=f"Checks: `{error.args[0]}`",
                ctx=ctx
            )
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)
            log.debug(f"{ctx.author} missing permissions {error.args[0]=} in {ctx.guild.name=}")

        elif isinstance(error, (errors.NotOwner)):
            embed = self._get_error_embed(
                title="You are not the owner of this bot",
                body=f"Only the owner can use `{ctx.command}`",
                ctx=ctx
            )
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)
            log.debug(f"{ctx.author} Tried to run a IsOwner command '{ctx.command}'")

        elif isinstance(error, (errors.NoPrivateMessage)):
            embed = self._get_error_embed(
                title="Cannot run in private",
                body=f"`{ctx.command}` cannot be ran as a private message, you must run command in a guild",
                ctx=ctx
            )
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)
            log.debug(f"{ctx.author} Tried to run NoPrivateMessage command '{ctx.command}'")

        elif isinstance(error, (errors.PrivateMessageOnly)):
            embed = self._get_error_embed(
                title="Can run only in private",
                body=f"You must run `{ctx.command}` as a direct message to this bot",
                ctx=ctx
            )
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)
            log.debug(f"{ctx.author} Tried to run PrivateMessageOnly command '{ctx.command}'")

        elif isinstance(error, (errors.NSFWChannelRequired)):
            embed = self._get_error_embed(
                title="Not a NSFW channel",
                body=f"You must run `{ctx.command}` in a NSFW channel to work",
                ctx=ctx
            )
            await ctx.send(embed=embed, delete_after=AUTO_DELETE_TIME)
            log.debug(f"{ctx.author} Tried to run NSFWChannelRequired command '{ctx.command}'")

        else:
            await self.handle_unexpected_error(ctx, error)

    # General HTTP error handle
    @staticmethod
    async def handle_api_error(ctx: Context, error) -> None:
        """
        Send an error message embed and log it.

        Handled errors:
            404 - Not Found
            400 - Bad Request
            500:599 - Server errors

        Args:
            ctx (Context): Discord context object, needed for author and timestamps.
            error (errors.CheckFailure): The error that was raised.
        """
        if error.status == 404:
            await ctx.send("There does not seem to be anything matching your query.",
                delete_after=AUTO_DELETE_TIME)
            log.debug(f"API responded with 404 for command {ctx.command}")

        elif error.status == 400:
            await ctx.send("According to the API, your request is malformed.",
                delete_after=AUTO_DELETE_TIME)
            content = await error.response.json()
            log.debug(f"API responded with 400 for command {ctx.command}: %r.", content)

        elif 500 <= error.status < 600:
            await ctx.send("Sorry, there seems to be an internal issue with the API.",
                delete_after=AUTO_DELETE_TIME)
            log.warning(f"API responded with {error.status} for command {ctx.command}")

        else:
            await ctx.send(
                f"Got an unexpected status code from the API (`{error.status}`).",
                delete_after=AUTO_DELETE_TIME
            )
            log.warning(
                f"Unexpected API response for command {ctx.command}: {error.status}"
            )

    # Ceatch all for unknown errors
    @staticmethod
    async def handle_unexpected_error(ctx: Context, error: errors.CommandError) -> None:
        """Send a generic error message and log the exception as an error.

        Args:
            ctx (Context): Discord context object, needed for author and timestamps.
            error (errors.CheckFailure): The error that was raised.
        """
        await ctx.send(
            f"Sorry, an unexpected error occurred. Please let us know!\n\n"
            f"```{error.__class__.__name__}: {error}```"
        )

        #TODO: Make channel to report these errors.

        log.error(f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}", exc_info=error)

class ResponseCodeError(ValueError):
    """Raised when a non-OK HTTP response is received."""

    def __init__(
        self,
        response: aiohttp.ClientResponse,
        response_json: Optional[dict] = None,
        response_text: str = ""
    ):
        self.status = response.status
        self.response_json = response_json or {}
        self.response_text = response_text
        self.response = response

    def __str__(self):
        response = self.response_json if self.response_json else self.response_text
        return f"Status: {self.status} Response: {response}"

def setup(bot) -> None:
    """Load the error_handle cog."""
    bot.add_cog(error_handle(bot))
    log.info("Listener loaded: error_handle")
