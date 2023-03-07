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


class AdministrationCommands(Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.eval_command = app_commands.ContextMenu(name="Eval", callback=self.eval)
        self._last_result = None
        self.bot.tree.add_command(self.eval_command)

    def app_is_owner(self, ctx: discord.Interaction, *kwargs):
        return self.bot.is_owner(ctx.user)

    @app_commands.check(app_is_owner)
    class AdminGroup(app_commands.Group):
        pass
    admin = AdminGroup(name="admin", guild_ids=[config["guild_id"]])
    sync = AdminGroup(name="sync", parent=admin)

    def _cleanup_code(self, content: str) -> str:
        """
        Automatically removes code blocks from the code.
        """
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    async def eval(self, ctx: discord.Interaction, message: discord.Message):
        """
        Evaluates input as Python code.
        """
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
        body = self._cleanup_code(body)
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

    @sync.command(name="global", description="Sync commands globally.")
    async def sync_global(self, ctx: discord.Interaction) -> None:
        """
        Does not sync all commands globally, just the ones registered as global.
        """
        await ctx.response.defer()
        synced = await self.bot.tree.sync()
        await embeds.success_message(ctx=ctx, description=f"Synced {len(synced)} commands globally.")

    @sync.command(name="guild", description="Sync commands in the current guild")
    async def sync_guild(self, ctx: discord.Interaction) -> None:
        """
        Does not sync all of your commands to that guild, just the ones registered to that guild.
        """
        await ctx.response.defer()
        synced = await self.bot.tree.sync(guild=ctx.guild)
        await embeds.success_message(ctx=ctx, description=f"Synced {len(synced)} commands to the guild.")

    @sync.command(name="copy", description="Copies all global app commands to current guild and syncs")
    async def sync_global_to_guild(self, ctx: discord.Interaction) -> None:
        """
        This will copy the global list of commands in the tree into the list of commands for the specified guild.
        This is not permanent between bot restarts.
        """
        await ctx.response.defer()
        self.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await self.bot.tree.sync(guild=ctx.guild)
        await embeds.success_message(ctx=ctx, description=f"Synced {len(synced)} global commands to the current guild.")

    @sync.command(name="remove", description="Clears all commands from the current guild target and syncs")
    async def sync_remove(self, ctx: discord.Interaction) -> None:
        await ctx.response.defer()
        self.bot.tree.clear_commands(guild=ctx.guild)
        await self.bot.tree.sync(guild=ctx.guild)
        await embeds.success_message(ctx=ctx, description="Cleared all commands from the current guild and synced.")

    @sync_global.error
    @sync_guild.error
    @sync_global_to_guild.error
    @sync_remove.error
    async def sync_error(self, ctx: discord.Interaction, error: discord.HTTPException) -> None:
        await ctx.response.defer()

        if isinstance(error, discord.app_commands.errors.MissingRole):
            embed = embeds.error_embed(ctx=ctx, description=f"<@&{error.missing_role}> is required for this command.")
            await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdministrationCommands(bot))
    log.info("Commands loaded: administration")
