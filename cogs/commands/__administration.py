import io
import logging
import textwrap
import traceback
from contextlib import redirect_stdout

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Cog, Context
from discord_slash.utils.manage_commands import remove_all_commands

from utils import embeds
from utils.config import config
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class AdministrationCog(Cog):
    """Administration Cog Cog"""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    def _cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @commands.before_invoke(record_usage)
    @commands.group(aliases=["u", "ul"])
    async def utilities(self, ctx):
        return

    @commands.is_owner()
    @utilities.command(name="ping")
    async def ping(self, ctx):
        """Returns the Discord WebSocket latency."""
        await ctx.send(f"{round(self.bot.latency * 1000)}ms.")

    @commands.is_owner()
    @utilities.command(name="removecmds")
    async def removecmds(self, ctx):
        await remove_all_commands(bot_id=self.bot.user.id, bot_token=config["bot"]["token"], guild_ids=config["guild_ids"])

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
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "embeds": embeds,
            "_": self._last_result,
        }
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
            await ctx.send(embed=embed)
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
            await ctx.send(embed=embed)

        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\u2705")
            except Exception:
                pass

            if ret is None:
                if value:
                    # Output.
                    output = f"```py\n{value}\n```"
                    embed.add_field(name="Output:", value=output, inline=False)
                    await ctx.send(embed=embed)
            else:
                # Maybe the case where there's no output?
                self._last_result = ret
                output = f"```py\n{value}{ret}\n```"
                embed.add_field(name="Output:", value=output, inline=False)
                await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="rules")
    async def rules(self, ctx: Context):
        """Generates the #rules channel embeds."""
        embed = embeds.make_embed(color=0x7d98e9)
        embed.set_image(url="https://cdn.discordapp.com/attachments/835088653981581312/902441305836244992/AnimePiracy-Aqua-v2-Revision5.7.png")
        await ctx.send(embed=embed)

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
                "NSFL content is described as \"content which is so nauseating or disturbing that it might be emotionally scarring to view.\" Content marked NSFL may contain fetish pornography, gore, or lethal violence.\n\n"

                "**12. Egregious profiles are not allowed**\n"
                "Users with excessively offensive usernames, nicknames, avatars, server profiles, or statuses may be asked to change the offending content or may be preemptively banned in more severe cases."
                ),
            color=0x7d98e9
        )

        await ctx.send(embed=embed)
        await ctx.message.delete()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="createticketembed")
    async def create_ticket_embed(self, ctx: Context):
        embed = embeds.make_embed(
            title="🎫 Create a new modmail ticket",
            description="Click the react below to create a new modmail ticket.",
            color="default",
        )
        embed.add_field(
            name="Warning:",
            value="Serious inquiries only. Abuse may result in warning or ban.",
        )
        spawned = await ctx.send(embed=embed)
        await spawned.add_reaction("🎫")
        await ctx.message.delete()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="createcolorrolesembed", aliases=["ccre"])
    async def create_color_roles_embed(self, ctx: Context):
        embed = discord.Embed(
            description=(
                "You can react to one of the squares below to be assigned a colored user role. "
                f"If you are interested in a different color, you can become a <@&{config['roles']['nitro_booster']}> "
                "to receive a custom colored role."
            )
        )

        msg = await ctx.send(embed=embed)

        # API call to fetch all the emojis to cache, so that they work in future calls
        emotes_guild = await ctx.bot.fetch_guild(config["emoji_guild_ids"][0])
        await emotes_guild.fetch_emojis()

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
    @commands.command(name="createassignablerolesembed", aliases=["care"])
    async def create_assignable_roles_embed(self, ctx: Context):
        role_assignment_text = """
        You can react to one of the emotes below to assign yourself an event role.

        🎁  <@&832528733763928094> - Receive giveaway pings.
        📢  <@&827611682917711952> - Receive server announcement pings.
        📽  <@&831999443220955136> - Receive group watch event pings.
        <:kakeraW:830594599001129000>  <@&832512304334766110> - Receive Mudae event and season pings.
        🧩  <@&832512320306675722> - Receive Rin event pings.
        """
        embed = discord.Embed(description=role_assignment_text)
        msg = await ctx.send(embed=embed)

        # API call to fetch all the emojis to cache, so that they work in future calls
        emotes_guild = await ctx.bot.fetch_guild(config["emoji_guild_ids"][0])
        await emotes_guild.fetch_emojis()

        await msg.add_reaction("🎁")
        await msg.add_reaction("📢")
        await msg.add_reaction("📽")
        await msg.add_reaction(":kakeraW:830594599001129000")
        await msg.add_reaction("🧩")
        await ctx.message.delete()


def setup(bot: Bot) -> None:
    """Load the AdministrationCog cog."""
    bot.add_cog(AdministrationCog(bot))
    log.info("Commands loaded: administration")
