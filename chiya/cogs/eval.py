import io
import textwrap
import traceback
from contextlib import redirect_stdout

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Cog

from chiya.config import config
from chiya.utils import embeds


class EvalCog(Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.eval_command = app_commands.ContextMenu(name="Eval", callback=self.eval)
        self._last_result = None
        self.bot.tree.add_command(self.eval_command)

    def _cleanup_code(self, content: str) -> str:
        """Automatically removes code blocks from the code."""
        if content.startswith("```") and content.endswith("```"):
            lines = content.splitlines()
            if len(lines) == 1:
                return content[3:-3]

            return "\n".join(lines[1:-1])

        return content.strip("` \n")

    async def _get_eval_body(self, message: discord.Message) -> str:
        body = message.content or ""
        if body:
            return self._cleanup_code(body)

        for attachment in message.attachments:
            if attachment.filename.endswith(".py"):
                return self._cleanup_code((await attachment.read()).decode("utf-8", errors="replace"))

        return ""

    def _build_eval_env(self, ctx: discord.Interaction, message: discord.Message) -> dict:
        env = globals().copy()
        env.update(
            {
                "bot": self.bot,
                "ctx": ctx,
                "channel": ctx.channel,
                "author": ctx.user,
                "guild": ctx.guild,
                "message": message,
                "embeds": embeds,
                "_": self._last_result,
            }
        )
        return env

    def _add_eval_field(
        self,
        embed: discord.Embed,
        files: list[discord.File],
        *,
        name: str,
        content: str,
        filename: str,
        language: str = "py",
    ) -> None:
        wrapped = f"```{language}\n{content}\n```"
        if len(wrapped) <= 1024:
            embed.add_field(name=name, value=wrapped, inline=False)
            return

        embed.add_field(name=name, value=f"Attached as `{filename}`.", inline=False)
        files.append(discord.File(io.BytesIO(content.encode("utf-8")), filename=filename))

    @app_commands.guilds(config.guild_id)
    async def eval(self, ctx: discord.Interaction, message: discord.Message) -> None:
        """Evaluates input as Python code."""

        await ctx.response.defer(thinking=True, ephemeral=True)

        if not await self.bot.is_owner(ctx.user):
            await embeds.send_error(ctx=ctx, description="You do not own this bot.")
            return

        body = await self._get_eval_body(message)
        if not body:
            await embeds.send_error(ctx=ctx, description="No code was provided.")
            return

        env = self._build_eval_env(ctx, message)
        embed = discord.Embed(title="Evaluating.", color=0xB134EB)
        files: list[discord.File] = []
        self._add_eval_field(embed, files, name="Input:", content=body, filename="input.py")

        stdout = io.StringIO()
        to_compile = f"async def func():\n{textwrap.indent(body, '    ')}"

        try:
            exec(to_compile, env)
        except Exception as e:
            self._add_eval_field(
                embed,
                files,
                name="Errors:",
                content=f"{e.__class__.__name__}: {e}",
                filename="compile_error.txt",
            )
            await ctx.followup.send(embed=embed, files=files)
            return

        try:
            with redirect_stdout(stdout):
                ret = await env["func"]()
        except Exception:
            self._add_eval_field(
                embed,
                files,
                name="Errors:",
                content=f"{stdout.getvalue()}{traceback.format_exc()}",
                filename="runtime_error.txt",
            )
            await ctx.followup.send(embed=embed, files=files)
            return

        try:
            await message.add_reaction("\u2705")
        except Exception:
            pass

        output = stdout.getvalue()
        if ret is not None:
            self._last_result = ret
            output = f"{output}{ret}"

        self._add_eval_field(
            embed,
            files,
            name="Output:",
            content=output or "No return value!",
            filename="output.txt",
        )
        await ctx.followup.send(embed=embed, files=files)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EvalCog(bot))
