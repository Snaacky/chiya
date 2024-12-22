import io
import os
import textwrap
import traceback
from contextlib import redirect_stdout

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Cog
from loguru import logger as log

from chiya.config import config
from chiya.utils import embeds


class BotCommands(Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.eval_command = app_commands.ContextMenu(name="Eval", callback=self.eval)
        self._last_result = None
        self.bot.tree.add_command(self.eval_command)

    def app_is_owner(self, interaction: discord.Interaction, *kwargs):
        return self.bot.is_owner(interaction.user)

    class BotGroup(app_commands.Group):
        pass

    bot = BotGroup(name="bot", guild_ids=[config.guild_id])

    @app_commands.guilds(config.guild_id)
    @app_commands.guild_only()
    async def eval(self, ctx: discord.Interaction, message: discord.Message):
        """Evaluates input as Python code."""

        def _cleanup_code(self, content: str) -> str:
            """Automatically removes code blocks from the code."""
            if content.startswith("```") and content.endswith("```"):  # remove ```py\n```
                split_code = content.split("\n")
                if len(split_code) == 1:
                    return content.split("```")[1]
                else:
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
        body = _cleanup_code(self, body)
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

    @bot.command(name="ping", description="Get bot latency")
    async def ping(self, ctx: discord.Interaction):
        await ctx.response.defer(thinking=True, ephemeral=True)
        await ctx.followup.send(f"Pong! {round (self.bot.latency * 1000)}ms.")

    @bot.command(name="console", description="Get console output")
    async def console(self, ctx: discord.Interaction, lines: int):
        await ctx.response.defer(thinking=True, ephemeral=True)
        if lines >= 500:
            return await embeds.error_message(ctx=ctx, description="Please specify <= 500 lines max.")
        with open(os.path.join("logs", "bot.log")) as f:
            lines = f.readlines()[-lines:]
        with io.StringIO() as file:
            file.write("".join(lines))
            file.seek(0)
            in_memory = discord.File(file, filename="output.log")
        await ctx.followup.send(file=in_memory)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotCommands(bot))
    log.info("Commands loaded: bot")
