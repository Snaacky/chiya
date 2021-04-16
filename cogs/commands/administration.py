import logging
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, Greedy
from discord.ext.commands.converter import RoleConverter

import config
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class AdministrationCog(Cog):
    """ Administration Cog Cog """

    def __init__(self, bot):
        self.bot = bot

    @commands.has_role(config.role_admin)
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
        embed.add_field(name="Seadex:", inline=True, value="> [seadex.piracy.moe](https://seadex.piracy.moe)")
        embed.add_field(name="GitHub:", inline=True, value="> [github.com/ranimepiracy](https://github.com/ranimepiracy)")
        embed.add_field(name="Twitter:", inline=True, value="> [@ranimepiracy](https://twitter.com/ranimepiracy)")
        embed.add_field(name="Uptime Status:", inline=True, value="> [status.piracy.moe](https://status.piracy.moe/)")
        await ctx.send(embed=embed)

        # Clean up the command invoker
        await ctx.message.delete()


    @commands.has_role(config.role_admin)
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


    @commands.has_role(config.role_admin)
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="createcolorrolesembed", aliases=['ccre'])
    async def create_color_roles_embed(self, ctx: Context):
        embed = discord.Embed(description=f"You can react to one of the squares below to be assigned a colored user role. If you are interested in a different color, you can become a <@&{config.role_server_booster}> to receive a custom colored role.")
        msg = await ctx.send(embed=embed)

        # API call to fetch all the emojis to cache, so that they work in future calls
        emotes_guild = await ctx.bot.fetch_guild(config.emoji_guild_id)
        emojis = await emotes_guild.fetch_emojis()
        
        await msg.add_reaction(":redsquare:805032092907601952")
        await msg.add_reaction(":orangesquare:805032107952308235")
        await msg.add_reaction(":yellowsquare:805032120971165709")
        await msg.add_reaction(":greensquare:805032132325801994")
        await msg.add_reaction(":bluesquare:805032145030348840")
        await msg.add_reaction(":pinksquare:805032162197635114")
        await msg.add_reaction(":purplesquare:805032172074696744")
        await ctx.message.delete()
    
    @commands.has_role(config.role_admin)
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @commands.command(name="createassignablerolesembed", aliases=['care'])
    async def create_color_roles_embed(self, ctx: Context):
        role_assignment_text = """
        You can react to one of the emotes below to assign yourself an event role\n
        
        🎁 `Giveaway Events` - Receives giveaway pings.\n
        📢 `Server Announcements` - Receives server announcement pings.\n
        📽 `Watch Party` - Receives group watch event pings.\n
        <:kakeraW:830594599001129000> `Mudae Player` - Receives Mudae event pings.\n
        🎲 `Rin Player` - Receives Rin event pings.\n
        <:pickaxe:831765423455993888> `Minecraft` - Receives Minecraft event pings.\n
        🕹 `Community Events` - Receive other community event pings (such as gaming).\n
        """
        embed = discord.Embed(description=role_assignment_text)
        msg = await ctx.send(embed=embed)

        # API call to fetch all the emojis to cache, so that they work in future calls
        emotes_guild = await ctx.bot.fetch_guild(config.emoji_guild_id)
        emojis = await emotes_guild.fetch_emojis()
        
        await msg.add_reaction("🎁")
        await msg.add_reaction("📢")
        await msg.add_reaction("📽")
        await msg.add_reaction(":kakeraW:830594599001129000")
        await msg.add_reaction("🎲")
        await msg.add_reaction(":pickaxe:831765423455993888")
        await msg.add_reaction("🕹")
        await ctx.message.delete()


def setup(bot: Bot) -> None:
    """ Load the AdministrationCog cog. """
    bot.add_cog(AdministrationCog(bot))
    log.info("Cog loaded: AdministrationCog")
