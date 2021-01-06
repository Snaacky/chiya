import traceback
import logging
import io
import textwrap
from contextlib import redirect_stdout
import discord
from discord.ext import commands
from discord.ext.commands.core import is_owner

import utils  # pylint: disable=import-error
from utils.record import record_usage  # pylint: disable=import-error

log = logging.getLogger(__name__)


class UtilitiesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.before_invoke(record_usage)
    @commands.is_owner()
    @commands.group(aliases=["u", "ul"])
    async def utilities(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('No utilities subcommand specified.')

    @utilities.command(name="ping")
    async def ping(self, ctx):
        """ Returns the Discord WebSocket latency. """
        print("Ping subcommand invoked.")
        await ctx.send(f"Client Latency is:{round(self.bot.latency * 1000)}ms.")

    @utilities.command(name="count")
    async def count(self, ctx):
        """ Returns the current guild member count. """
        await ctx.send(ctx.guild.member_count)

    @utilities.command(name="say")
    async def say(self, ctx, *, args):
        """ Echos the input argument. """
        await ctx.send(args)

    @utilities.command(name="eval")
    async def eval(self, ctx, *, body: str):
        """Evaluates input as Python code."""
        # Required environment variables.
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        # Creating embed.
        embed = discord.Embed(title="Evaluating.", color=0xb134eb)
        env.update(globals())

        # Calling cleanup command to remove the markdown traces.
        body = self.cleanup_code(body)
        embed.add_field(
            name="Input:", value=f"```py\n{body}\n```", inline=False)
        # Output stream.
        stdout = io.StringIO()

        # Exact code to be compiled.
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            # Attempting execution
            exec(to_compile, env)
        except Exception as e:
            # In case there's an error, add it to the embed, send and stop.
            errors = f'```py\n{e.__class__.__name__}: {e}\n```'
            embed.add_field(name="Errors:", value=errors, inline=False)
            await ctx.send(embed=embed)
            return errors

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            # In case there's an error, add it to the embed, send and stop.
            value = stdout.getvalue()
            errors = f'```py\n{value}{traceback.format_exc()}\n```'
            embed.add_field(name="Errors:", value=errors, inline=False)
            await ctx.send(embed=embed)

        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    # Output.
                    output = f'```py\n{value}\n```'
                    embed.add_field(
                        name="Output:", value=output, inline=False)
                    await ctx.send(embed=embed)
            else:
                # Maybe the case where there's no output?
                self._last_result = ret
                output = f'```py\n{value}{ret}\n```'
                embed.add_field(name="Output:", value=output, inline=False)
                await ctx.send(embed=embed)

    @utilities.command(name="reload")
    async def reload_cog(self, ctx, *, module):
        """ Reloads specified cog/module. Remember the directory structures. """
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')

        else:
            await ctx.message.add_reaction("✔")
            await ctx.send(f"Reloaded the {module} module.")


def setup(bot) -> None:
    """ Load the UtilitiesCog cog. """
    bot.add_cog(UtilitiesCog(bot))
    log.info("Cog loaded: UtilitiesCog")
