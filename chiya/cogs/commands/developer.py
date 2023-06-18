import io
import logging
import os
import textwrap
import traceback
from contextlib import redirect_stdout

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Cog

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class DevCommands(Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.eval_command = app_commands.ContextMenu(name="Eval", callback=self.eval)
        self._last_result = None
        self.bot.tree.add_command(self.eval_command)

    def app_is_owner(self, interaction: discord.Interaction, *kwargs):
        return self.bot.is_owner(interaction.user)

    class DevGroup(app_commands.Group):
        pass
    dev = DevGroup(name="dev", guild_ids=[config["guild_id"]])

    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    async def eval(self, ctx: discord.Interaction, message: discord.Message):
        """Evaluates input as Python code."""
        def _cleanup_code(self, content: str) -> str:
            """Automatically removes code blocks from the code."""
            if content.startswith("```") and content.endswith("```"):  # remove ```py\n```
                return "\n".join(content.split("\n")[1:-1])
            return content.strip("` \n")  # remove `foo`
        await ctx.response.defer(thinking=True, ephemeral=True)

        if not await self.bot.is_owner(ctx.user):
            return await embeds.error_message(ctx=ctx, description="You do not own this bot.")
        # Required environment variables.
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.user,
            "guild": ctx.guild,
            "message": message,
            "embeds": embeds,
            "_": self._last_result,
        }

        body = message.content
        if not body:
            for attach in message.attachments:
                _, file_extension = os.path.splitext(attach.filename)
                if "text/x-python" in attach.content_type and file_extension == ".py":
                    read = await attach.read()
                    body = read.decode("utf-8")
                    break

        # Creating embed.
        embed = discord.Embed(title="Evaluating.", color=0xB134EB)
        env.update(globals())

        # Calling cleanup command to remove the markdown traces.
        body = _cleanup_code(body)
        embed.add_field(name="Input:", value=f"```py\n{body}\n```", inline=False)
        # Output stream.
        stdout = io.StringIO()

        # Exact code to be compiled.
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            # Attempting execution
            exec(to_compile, env)
        except Exception as e:
            # In case there's an error, add it to the embed, send and stop.
            errors = f"```py\n{e.__class__.__name__}: {e}\n```"
            embed.add_field(name="Errors:", value=errors, inline=False)
            await ctx.followup.send(embed=embed)
            return errors

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            # In case there's an error, add it to the embed, send and stop.
            value = stdout.getvalue()
            errors = f"```py\n{value}{traceback.format_exc()}\n```"
            embed.add_field(name="Errors:", value=errors, inline=False)
            await ctx.followup.send(embed=embed)

        else:
            value = stdout.getvalue()
            try:
                await message.add_reaction("\u2705")
            except Exception:
                pass

            if ret is None:
                if value:
                    # Output.
                    output = f"```py\n{value}\n```"
                    embed.add_field(name="Output:", value=output, inline=False)
                else:
                    # no output, so remove the "bot is thinking... message"
                    embed.add_field(name="Output:", value="No return value!", inline=False)
                await ctx.followup.send(embed=embed)
            else:
                # Maybe the case where there's no output?
                self._last_result = ret
                output = f"```py\n{value}{ret}\n```"
                embed.add_field(name="Output:", value=output, inline=False)
                await ctx.followup.send(embed=embed)

    @dev.command(name="ping", description="Get bot latency")
    async def ping(self, ctx: discord.Interaction):
        await ctx.response.defer(thinking=True, ephemeral=True)
        await ctx.followup.send(f"Pong! {round (self.bot.latency * 1000)}ms.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DevCommands(bot))
    log.info("Commands loaded: dev")
