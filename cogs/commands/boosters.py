import logging

from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_permission

from utils.config import config
from utils import embeds


log = logging.getLogger(__name__)


class BoostersCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="boosters",
        description="List all the current server boosters",
        guild_ids=[config["guild_id"]],
        default_permission=False,
        permissions={
            config["guild_id"]: [
                create_permission(config["roles"]["staff"], SlashCommandPermissionType.ROLE, True),
                create_permission(config["roles"]["trial_mod"], SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def boosters(self, ctx: SlashContext):
        """
        Slash command for getting the current list of server boosters.

        Args:
            ctx (SlashContext): The context of the slash command.
        """
        await ctx.defer()

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Total boosts: {ctx.guild.premium_subscription_count}",
            thumbnail_url="https://i.imgur.com/22ZZG7h.png",
            color="nitro_pink",
            author=False
        )
        embed.description = "\n".join(user.mention for user in ctx.guild.premium_subscribers)
        embed.set_footer(text=f"Total boosters: {len(ctx.guild.premium_subscribers)}")
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(BoostersCog(bot))
    log.info("Commands loaded: boosters")
