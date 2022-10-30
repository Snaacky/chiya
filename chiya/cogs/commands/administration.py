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
    """
    This class is legacy code that needs to eventually be
    split into separate files and removed from the codebase.

    The eval command cannot be ported to slash commands until Discord
    supports slash command parameters with multiple lines of input.

    We will eventually migrate the embed generators into a slash
    command based embed generator system where the embed generators
    below will be stored as presets that can be spawned via slash
    commands.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.eval_command = app_commands.ContextMenu(name="Eval", callback=self.eval)
        self._last_result = None
        self.bot.tree.add_command(self.eval_command)

    def app_is_owner(self, interaction: discord.Interaction, *kwargs):
        return self.bot.is_owner(interaction.user)

    @app_commands.check(app_is_owner)
    class AdminGroup(app_commands.Group):
        pass
    admin = AdminGroup(name="admin", description="Admin commands", guild_ids=[config["guild_id"]])

    embed = AdminGroup(name="embed", description="Embed creation commands", parent=admin)
    sync = AdminGroup(name="sync", description="Sync commands", parent=admin)

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


    #[[
    # EMBED COMMANDS
    # ]]

    @embed.command(name="rules", description="Sends rule message to channel")
    async def rules(self, ctx: discord.Interaction) -> None:
        """Generates the #rules channel embeds."""
        await ctx.response.defer(ephemeral=True,thinking=True)

        embed = embeds.make_embed(color=0x7D98E9)
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/835088653981581312/902441305836244992/AnimePiracy-Aqua-v2-Revision5.7.png"
        )
        await ctx.channel.send(embed=embed)

        embed = embeds.make_embed(
            description=(
                "**1. Do not share copyright infringing files or links**\n"
                "Sharing illegal streaming sites, downloads, torrents, magnet links, trackers, NZBs, or any other form of warez puts our community at risk of being shut down. We are a discussion community, not a file-sharing hub.\n\n"
                "**2. Treat others the way you want to be treated**\n"
                "Attacking, belittling, or instigating drama with others will result in your removal from the community. Any form of prejudice, including but not limited to race, religion, gender, sexual identity, or ethnic background, will not be tolerated.\n\n"
                "**3. Do not disrupt chat**\n"
                "Avoid spamming, derailing conversations, trolling, posting in the incorrect channel, or disregarding channel rules. We expect you to make a basic attempt to fit in and not cause problems.\n\n"
                "**4. Do not abuse pings**\n"
                "Attempting to mass ping, spam ping, ghost ping, or harassing users with pings is not allowed. VIPs should not be pinged for help with their service. <@&763031634379276308> should only be pinged when the situation calls for their immediate attention.\n\n"
                "**5. Do not attempt to evade mod actions**\n"
                "Abusing the rules, such as our automod system, will not be tolerated. Subsequently, trying to find loopholes in the rules to evade mod action is not allowed and will result in a permanent ban.\n\n"
                "**6. Do not post unmarked spoilers**\n"
                "Be considerate and [use spoiler tags](https://support.discord.com/hc/en-us/articles/360022320632-Spoiler-Tags-) when discussing plot elements. Specify which title, series, or episode your spoiler is referencing outside the spoiler tag so that people don't blindly click a spoiler.\n\n"
                "**7. All conversation must be in English**\n"
                "No language other than English is permitted. We appreciate other languages and cultures, but we can only moderate the content we understand.\n\n"
                "**8. Do not post self-promotional content**\n"
                "We are not a billboard for you to advertise your Discord server, social media channels, referral links, personal projects, or services. Unsolicited spam via DMs will result in an immediate ban.\n\n"
                "**9. One account per person per lifetime**\n"
                "Anyone found sharing or using alternate accounts will be banned. Contact staff if you feel you deserve an exception.\n\n"
                "**10. Do not give away, trade, or misuse invites**\n"
                "Invites are intended for personal acquaintances. Publicly offering, requesting, or giving away invites to private trackers, DDL communities, or Usenet indexers is not allowed.\n\n"
                "**11. Do not post NSFL content**\n"
                'NSFL content is described as "content which is so nauseating or disturbing that it might be emotionally scarring to view." Content marked NSFL may contain fetish pornography, gore, or lethal violence.\n\n'
                "**12. Egregious profiles are not allowed**\n"
                "Users with excessively offensive usernames, nicknames, avatars, server profiles, or statuses may be asked to change the offending content or may be preemptively banned in more severe cases."
            ),
            color=0x7D98E9,
        )

        await ctx.channel.send(embed=embed)
        await ctx.followup.send("Rules added!", ephemeral=True)

    @embed.command(name="colorroles", description="Create the color roles embed message")
    async def create_color_roles_embed(self, ctx: discord.Interaction) -> None:
        await ctx.response.defer(ephemeral=True,thinking=True)
        embed = discord.Embed(
            description=(
                "You can react to one of the squares below to be assigned a colored user role. "
                f"If you are interested in a different color, you can become a <@&{config['roles']['nitro_booster']}> "
                "to receive a custom colored role."
            )
        )

        msg = await ctx.channel.send(embed=embed)

        # API call to fetch all the emojis to cache, so that they work in future calls
        emotes_guild = await self.bot.fetch_guild((config["emoji_guild_ids"][0]))
        await emotes_guild.fetch_emojis()

        await msg.add_reaction(":redsquare:805032092907601952")
        await msg.add_reaction(":orangesquare:805032107952308235")
        await msg.add_reaction(":yellowsquare:805032120971165709")
        await msg.add_reaction(":greensquare:805032132325801994")
        await msg.add_reaction(":bluesquare:805032145030348840")
        await msg.add_reaction(":pinksquare:805032162197635114")
        await msg.add_reaction(":purplesquare:805032172074696744")
        await ctx.followup.send("Color messaged sent!", ephemeral=True)

    @embed.command(name="reactroles", description="Create the assignable roles embed message")
    async def create_assignable_roles_embed(self, ctx: discord.Interaction) -> None:
        await ctx.response.defer(ephemeral=True,thinking=True)
        role_assignment_text = """
        You can react to one of the emotes below to assign yourself an event role.

        🎁  <@&832528733763928094> - Receive giveaway pings.
        📢  <@&827611682917711952> - Receive server announcement pings.
        📽  <@&831999443220955136> - Receive group watch event pings.
        <:kakeraW:830594599001129000>  <@&832512304334766110> - Receive Mudae event and season pings.
        🧩  <@&832512320306675722> - Receive Rin event pings.
        """
        embed = discord.Embed(description=role_assignment_text)
        msg = await ctx.channel.send(embed=embed)

        # API call to fetch all the emojis to cache, so that they work in future calls
        emotes_guild = await ctx.client.fetch_guild(config["emoji_guild_ids"][0])
        await emotes_guild.fetch_emojis()

        await msg.add_reaction("🎁")
        await msg.add_reaction("📢")
        await msg.add_reaction("📽")
        await msg.add_reaction(":kakeraW:830594599001129000")
        await msg.add_reaction("🧩")
        await ctx.followup.send("Rules added!", ephemeral=True)

    #[[
    # SYNC COMMANDS
    # ]]

    @sync.command(name="global", description="Sync commands globally.")    
    async def sync_global(self, interaction: discord.Interaction) -> None:
        """
        Does not sync all commands globally, just the ones registered as global.
        """
        await interaction.response.defer()
        synced = await self.bot.tree.sync()
        await embeds.success_message(ctx=interaction, description=f"Synced {len(synced)} commands globally.")

    @sync.command(name="guild", description="Sync commands in the current guild")
    async def sync_guild(self, interaction: discord.Interaction) -> None:
        """
        Does not sync all of your commands to that guild, just the ones registered to that guild.
        """
        await interaction.response.defer()
        synced = await self.bot.tree.sync(guild=interaction.guild)
        await embeds.success_message(ctx=interaction, description=f"Synced {len(synced)} commands to the current guild.")

    @sync.command(name="copy", description="Copies all global app commands to current guild and syncs")
    async def sync_global_to_guild(self, interaction: discord.Interaction) -> None:
        """
        This will copy the global list of commands in the tree into the list of commands for the specified guild.
        This is not permanent between bot restarts, and it doesn't impact the state of the commands (you still have to sync).
        """
        await interaction.response.defer()
        self.bot.tree.copy_global_to(guild=interaction.guild)
        synced = await self.bot.tree.sync(guild=interaction.guild)
        await embeds.success_message(ctx=interaction, description=f"Copied and synced {len(synced)} global app commands to the current guild.")

    @sync.command(name="remove", description="Clears all commands from the current guild target and syncs")
    async def sync_remove(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.bot.tree.clear_commands(guild=interaction.guild)
        await self.bot.tree.sync(guild=interaction.guild)
        await embeds.success_message(ctx=interaction, description="Cleared all commands from the current guild and synced.")

    @sync_global.error
    @sync_guild.error
    @sync_global_to_guild.error
    @sync_remove.error
    async def sync_error(self, interaction: discord.Interaction, error: discord.HTTPException) -> None:
        await interaction.response.defer()

        if isinstance(error, discord.app_commands.errors.MissingRole):
            embed = embeds.error_embed(ctx=interaction, description=f"Role <@&{error.missing_role}> is required to use this command.")
            await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdministrationCommands(bot))
    log.info("Commands loaded: administration")
