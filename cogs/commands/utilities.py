import io
import logging
import textwrap
import traceback
from contextlib import redirect_stdout
import glob
import re

import discord
from discord.ext import commands
from discord.ext.commands.core import is_owner

from utils import embeds
from utils.record import record_usage
import config

log = logging.getLogger(__name__)


class UtilitiesCog(commands.Cog):
    """UtilitiesCog"""

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
    @commands.group(aliases=["u", "ul"])
    async def utilities(self, ctx):
        if ctx.invoked_subcommand is None:
            # Send the help command for this group
            await ctx.send_help(ctx.command)

    @commands.is_owner()
    @utilities.command(name="ping")
    async def ping(self, ctx):
        """Returns the Discord WebSocket latency."""
        print("Ping subcommand invoked.")
        await ctx.send(f"Client Latency is: {round(self.bot.latency * 1000)}ms.")

    @commands.has_role(config.role_mod)
    @utilities.command(aliases=["population", "pop"])
    async def count(self, ctx):
        """Returns the current guild member count."""
        await ctx.send(ctx.guild.member_count)

    @commands.has_role(config.role_mod)
    @utilities.command(name="say")
    async def say(self, ctx, *, args):
        """Echos the input argument."""
        await ctx.send(args)

    @commands.is_owner()
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
            'embeds': embeds,
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

    @commands.is_owner()
    @utilities.command(name="reload")
    async def reload_cog(self, ctx: commands.Context, name_of_cog: str = None):
        """ Reloads specified cog or all cogs. """

        regex = r"(?<=<).*(?=\..* object at 0x.*>)"
        if name_of_cog is not None and name_of_cog in ctx.bot.cogs:
            # Reload cog if it exists.
            cog = re.search(regex, str(ctx.bot.cogs[name_of_cog]))
            try:
                self.bot.reload_extension(cog.group())
                
            except commands.ExtensionError as e:
                await ctx.message.add_reaction("❌")
                await ctx.send(f'{e.__class__.__name__}: {e}')
            
            else:
                await ctx.message.add_reaction("✔")
                await ctx.send(f"Reloaded `{cog.group()}` module!")
        
        elif name_of_cog is None:
            # Reload all the cogs in the folder named cogs.
            # Skips over any cogs that start with '__' or do not end with .py.
            cogs = []
            try:
                for cog in glob.iglob("cogs/**/[!^_]*.py", recursive=True):
                    if "\\" in cog:  # Pathing on Windows.
                        self.bot.reload_extension(cog.replace("\\", ".")[:-3])
                    else:  # Pathing on Linux.
                        self.bot.reload_extension(cog.replace("/", ".")[:-3])
            except commands.ExtensionError as e:
                await ctx.message.add_reaction("❌")
                await ctx.send(f'{e.__class__.__name__}: {e}')

            else:
                await ctx.message.add_reaction("✔")
                await ctx.send("Reloaded all modules!")
        else:
            await ctx.message.add_reaction("❌")
            await ctx.send("Module not found, check spelling, it's case sensitive")


def setup(bot) -> None:
    """Load the UtilitiesCog cog."""
    bot.add_cog(UtilitiesCog(bot))
    log.info("Cog loaded: UtilitiesCog")
