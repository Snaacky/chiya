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


# Enabling logs
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
        print("Ping subcommand invoked.")
        await ctx.send(f"Client Latency is:{round(self.bot.latency*1000)}ms.")

    @utilities.command(name="members")
    async def members(self, ctx):
        await ctx.send(ctx.guild.member_count)

    @utilities.command(name="say")
    async def say(self, ctx, *, args):
        await ctx.send(args)

    @utilities.command(name="eval")
    async def eval(self, ctx, *, body: str):
        """Evaluates a code"""

        # required environment variables
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        # creating embed
        embedVar = discord.Embed(title="Evaluating.", color=0xb134eb)
        env.update(globals())

        # calling cleanup command to remove the markdown traces
        body = self.cleanup_code(body)
        embedVar.add_field(
            name="Input:", value=f"```py\n{body}\n```", inline=False)
        # output stream
        stdout = io.StringIO()

        # exact code to be compiled
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            # attempting execution
            exec(to_compile, env)
        except Exception as e:
            # in case there's an error, add it to the embed, send and stop
            errors = f'```py\n{e.__class__.__name__}: {e}\n```'
            embedVar.add_field(name="Errors:", value=errors, inline=False)
            await ctx.send(embed=embedVar)
            return errors

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            # in case there's an error, add it to the embed, send and stop
            value = stdout.getvalue()
            errors = f'```py\n{value}{traceback.format_exc()}\n```'
            embedVar.add_field(name="Errors:", value=errors, inline=False)
            await ctx.send(embed=embedVar)

        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    # Output
                    output = f'```py\n{value}\n```'
                    embedVar.add_field(
                        name="Output:", value=output, inline=False)
                    await ctx.send(embed=embedVar)
            else:
                # Maybe the case where there's no output?
                self._last_result = ret
                output = f'```py\n{value}{ret}\n```'
                embedVar.add_field(name="Output:", value=output, inline=False)
                await ctx.send(embed=embedVar)

    @utilities.command(name="reload")
    async def reload_cog(self, ctx, *, module):
        """Reloads specified cog/module. Remember the directory structures."""
        try:
            self.bot.reload_extension(module)

        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')

        else:
            await ctx.message.add_reaction("✔")
            await ctx.send(f"Reloaded the {module} module.")


def setup(bot) -> None:
    """Load the UtilitiesCog cog."""
    bot.add_cog(UtilitiesCog(bot))
    log.info("Cog loaded: UtilitiesCog")
