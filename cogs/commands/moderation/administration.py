import glob
import io
import logging
import re
import textwrap
import traceback
from contextlib import redirect_stdout

import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context

from cogs.commands import settings
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class AdministrationCog(Cog):
    """ Administration Cog Cog """

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    def _cleanup_code(self, content):
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
        await ctx.send(f"{round(self.bot.latency * 1000)}ms.")

    @commands.is_owner()
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
        body = self._cleanup_code(body)
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
            await ctx.send("Module not found, check spelling, it's case sensitive.")

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="rules")
    async def rules(self, ctx: Context):
        """ Generates the #rules channel embeds. """

        # Captain Karen header image embed
        embed = embeds.make_embed(color="quotes_grey")
        embed.set_image(url="https://i.imgur.com/Yk4kwZy.gif")
        await ctx.send(embed=embed)

        # The actual rules embed
        embed = embeds.make_embed(title="📃  Discord Server Rules", color="quotes_grey", description="This list is not all-encompassing and you may be actioned for a reason outside of these rules. Use common sense when interacting in our community.")
        embed.add_field(name="Rule 1: Do not send copyright-infringing material.", inline=False, value="> Linking to torrents, pirated stream links, direct download links, or uploading files over Discord puts our community at risk of being shut down. We are a discussion community, not a file-sharing hub.")
        embed.add_field(name="Rule 2: Be courteous and mindful of others.", inline=False, value="> Do not engage in toxic behavior such as spamming, derailing conversations, attacking other users, or attempting to instigate drama. Bigotry will not be tolerated. Avoid problematic avatars, usernames, or nicknames.")
        embed.add_field(name="Rule 3: Do not post self-promotional content.", inline=False, value="> We are not a billboard nor the place to advertise your Discord server, app, website, service, etc.")
        embed.add_field(name="Rule 4: Do not post unmarked spoilers.", inline=False, value="> Use spoiler tags and include what series or episode your spoiler is in reference to outside the spoiler tag so people don't blindly click a spoiler.")
        embed.add_field(name="Rule 5: Do not backseat moderate.", inline=False, value="> If you see someone breaking the rules or have something to report, please submit a <#829861810999132160> ticket.")
        embed.add_field(name="Rule 6: Do not abuse pings.", inline=False, value="> Do not ping staff outside of conversation unless necessary. Do not ping VIP users for questions or help with their service. Do not spam or ghost ping other users.")
        embed.add_field(name="Rule 7: Do not beg, buy, sell, or trade.", inline=False, value="> This includes, but is not limited to, server ranks, roles, permissions, giveaways, private community invites, or any digital or physical goods.")
        embed.add_field(name="Rule 8: Follow the Discord Community Guidelines and Terms of Service.", inline=False, value="> The Discord Community Guidelines and Terms of Service govern all servers on the platform. Please familarize yourself with them and the restrictions that come with them. \n> \n> https://discord.com/guidelines \n> https://discord.com/terms")
        await ctx.send(embed=embed)

        # /r/animepiracy links embed
        embed = embeds.make_embed(title="🔗  Our Links", color="quotes_grey")
        embed.add_field(name="Reddit:", inline=True, value="> [/r/animepiracy](https://reddit.com/r/animepiracy)")
        embed.add_field(name="Discord:", inline=True, value="> [discord.gg/piracy](https://discord.gg/piracy)")
        embed.add_field(name="Index:", inline=True, value="> [piracy.moe](https://piracy.moe)")
        embed.add_field(name="Wiki:", inline=True, value="> [wiki.piracy.moe](https://wiki.piracy.moe)")
        embed.add_field(name="Seadex:", inline=True, value="> [releases.moe](https://releases.moe)")
        embed.add_field(name="GitHub:", inline=True, value="> [github.com/ranimepiracy](https://github.com/ranimepiracy)")
        embed.add_field(name="Twitter:", inline=True, value="> [@ranimepiracy](https://twitter.com/ranimepiracy)")
        embed.add_field(name="Uptime Status:", inline=True, value="> [status.piracy.moe](https://status.piracy.moe/)")
        await ctx.send(embed=embed)

        # Clean up the command invoker
        await ctx.message.delete()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="createticketembed")
    async def create_ticket_embed(self, ctx: Context):
        embed = embeds.make_embed(title="🎫 Create a new modmail ticket",
                                  description="Click the react below to create a new modmail ticket.",
                                  color="default")
        embed.add_field(name="Warning:", value="Serious inquiries only. Abuse may result in warning or ban.")
        spawned = await ctx.send(embed=embed)
        await spawned.add_reaction("🎫")
        await ctx.message.delete()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="createcolorrolesembed", aliases=['ccre'])
    async def create_color_roles_embed(self, ctx: Context):
        embed = discord.Embed(description=f"You can react to one of the squares below to be assigned a colored user role. If you are interested in a different color, you can become a <@&{settings.get_value('role_server_booster')}> to receive a custom colored role.")
        msg = await ctx.send(embed=embed)

        # API call to fetch all the emojis to cache, so that they work in future calls
        emotes_guild = await ctx.bot.fetch_guild(settings.get_value("emoji_guild_id"))
        emojis = await emotes_guild.fetch_emojis()

        await msg.add_reaction(":redsquare:805032092907601952")
        await msg.add_reaction(":orangesquare:805032107952308235")
        await msg.add_reaction(":yellowsquare:805032120971165709")
        await msg.add_reaction(":greensquare:805032132325801994")
        await msg.add_reaction(":bluesquare:805032145030348840")
        await msg.add_reaction(":pinksquare:805032162197635114")
        await msg.add_reaction(":purplesquare:805032172074696744")
        await ctx.message.delete()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="createassignablerolesembed", aliases=['care'])
    async def create_assignable_roles_embed(self, ctx: Context):
        role_assignment_text = """
        You can react to one of the emotes below to assign yourself an event role.

        🎁  <@&832528733763928094> - Receive giveaway pings.
        📢  <@&827611682917711952> - Receive server announcement pings.
        📽  <@&831999443220955136> - Receive group watch event pings.
        <:kakeraW:830594599001129000>  <@&832512304334766110> - Receive Mudae event and season pings.
        🧩  <@&832512320306675722> - Receive Rin event pings.
        <:pickaxe:831765423455993888>  <@&832512327731118102> - Receive Minecraft server related pings.
        """
        embed = discord.Embed(description=role_assignment_text)
        msg = await ctx.send(embed=embed)

        # API call to fetch all the emojis to cache, so that they work in future calls
        emotes_guild = await ctx.bot.fetch_guild(settings.get_value("emoji_guild_id"))
        await emotes_guild.fetch_emojis()

        await msg.add_reaction("🎁")
        await msg.add_reaction("📢")
        await msg.add_reaction("📽")
        await msg.add_reaction(":kakeraW:830594599001129000")
        await msg.add_reaction("🧩")
        await msg.add_reaction(":pickaxe:831765423455993888")
        await ctx.message.delete()


def setup(bot: Bot) -> None:
    """ Load the AdministrationCog cog. """
    bot.add_cog(AdministrationCog(bot))
    log.info("Commands loaded: administration")
