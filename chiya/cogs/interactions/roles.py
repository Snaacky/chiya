import logging

import discord
from discord.ext import commands
from discord.commands import slash_command

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class RolesInteractions(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.is_owner()
    @slash_command(guild_ids=config["guild_ids"])
    async def color(self, ctx: discord.ApplicationContext):
        view_colors = ColorsDropdownView(self.bot)
        view_roles = RolesDropdownView(self.bot)

        embed_intro = embeds.make_embed(
            title="Roles Introduction",
            description="➜ **How do I get a role?** React to the emoji that corresponds with the desired role shown below!\n➜ **How do I get rid of a role?** Remove the reaction you have placed on the role.\n➜ **How do I switch roles?** Either react on a different role, or remove the previous reaction and react to the role you want.",
            color=12506302,
        )

        embed_colors = embeds.make_embed(
            title="Colors",
            description="Listed below are the cosmetic roles our server offers. If you are interested in a different color, you can become a server booster and receive a custom role (name, hex, and icon) for the duration of your boost.\n<:spacer:975178860607991839>",
            color=12506302,
        )
        embed_colors.add_field(
            name="Standard Colors <:happyramen:994039386264064080>",
            value="<:red:994048983892754584> » <@&974494536573284422>\n<:orange:994048968826822727> » <@&974494627090554920>\n<:yellow:994048954574573588> » <@&974494731809730610>\n<:green:994048941584826398> » <@&974494835341930506>\n<:blue:994048926112038932> » <@&974494972747325491>\n<:purple:994048906033901638> » <@&974495084848500736>\n<:pink:994048823037022209> » <@&974495184962326538>",
            inline=True,
        )
        embed_colors.add_field(name="<:spacer:975178860607991839>", value="<:spacer:975178860607991839>", inline=True)
        embed_colors.add_field(
            name="Exclusive Colors <:happyneko:994039519563239496>",
            value="<:gerberared:994049068433158304> » <@&974533561388531742>\n<:mikanorange:994049056248709200> » <@&974534009277284402>\n<:kiwigreen:994049042889838673> » <@&974534154110771220>\n<:hyacinthblue:994049028755038259> » <@&974534076109307914>\n<:violetpurple:994049015958212649> » <@&974534152982515813>\n<:snowywhite:994049000011472931> » <@&974534863023657000>",
            inline=True,
        )

        embed_pings = embeds.make_embed(
            title="Pings",
            description="To reduce the amount of @everyone pings, we use specific event roles instead. <:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839><:spacer:975178860607991839>\n:loudspeaker: » <@&974486635079147541>\n:gift: » <@&974485422023516262>\n:popcorn: » <@&975082113550413905>\n<:kakeraW:974923707560644608> » <@&974485442378498119>\n:jigsaw: » <@&974485460531441724>",
            color=12506302,
        )

        await ctx.send(embed=embed_intro)
        await ctx.send(embed=embed_colors)
        await ctx.send(view=view_colors)
        await ctx.send(embed=embed_pings)
        await ctx.send(view=view_roles)


class ColorsDropdown(discord.ui.Select):
    def __init__(self, bot: discord.Bot):
        options = [
            discord.SelectOption(label="Red", emoji="<:red:994048983892754584>"),
            discord.SelectOption(label="Orange", emoji="<:orange:994048968826822727>"),
            discord.SelectOption(label="Yellow", emoji="<:yellow:994048954574573588>"),
            discord.SelectOption(label="Green", emoji="<:green:994048941584826398>"),
            discord.SelectOption(label="Blue", emoji="<:blue:994048926112038932>"),
            discord.SelectOption(label="Purple", emoji="<:purple:994048906033901638>"),
            discord.SelectOption(label="Pink", emoji="<:pink:994048823037022209>"),
            discord.SelectOption(
                label="Gerbera Red", description="Tatsu level 10+", emoji="<:gerberared:994049068433158304>"
            ),
            discord.SelectOption(
                label="Mikan Orange", description="Tatsu level 10+", emoji="<:mikanorange:994049056248709200>"
            ),
            discord.SelectOption(
                label="Kiwi Green", description="Tatsu level 10+", emoji="<:kiwigreen:994049042889838673>"
            ),
            discord.SelectOption(
                label="Hyacinth Blue", description="Tatsu level 10+", emoji="<:hyacinthblue:994049028755038259>"
            ),
            discord.SelectOption(
                label="Violet Purple", description="Tatsu level 10+", emoji="<:violetpurple:994049015958212649>"
            ),
            discord.SelectOption(
                label="Snowy White", description="Tatsu level 10+", emoji="<:snowywhite:994049000011472931>"
            ),
        ]

        super().__init__(
            placeholder="Select your color...",
            min_values=0,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Not implememented but you can access via self.values[#]!")


class ColorsDropdownView(discord.ui.View):
    def __init__(self, bot: discord.Bot):
        super().__init__(ColorsDropdown(bot))


class RolesDropdown(discord.ui.Select):
    def __init__(self, bot: discord.Bot):
        options = [
            discord.SelectOption(label="Server Announcements", emoji="📢"),
            discord.SelectOption(label="Giveaway Events", emoji="🎁"),
            discord.SelectOption(label="Group Watch", emoji="🍿"),
            discord.SelectOption(label="Mudae Player", emoji="<:kakeraW:974923707560644608>"),
            discord.SelectOption(label="Rin Player", emoji="🧩"),
        ]

        super().__init__(
            placeholder="Select your roles...",
            min_values=0,
            max_values=5,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Not implememented but you can access via self.values[#]!")


class RolesDropdownView(discord.ui.View):
    def __init__(self, bot: discord.Bot):
        super().__init__(RolesDropdown(bot))


def setup(bot: commands.Bot) -> None:
    bot.add_cog(RolesInteractions(bot))
    log.info("Interactions loaded: roles")
