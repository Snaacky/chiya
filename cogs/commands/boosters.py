import logging

from discord.commands import Bot, Cog, permissions, slash_command, context

from utils.config import config
from utils import embeds


log = logging.getLogger(__name__)


class Boosters(Cog):

    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_id=config["guild_id"], default_permission=False, description="List all the server boosters")
    @permissions.has_role(config["roles"]["privileged"]["staff"])
    async def boosters(self, ctx: context.ApplicationContext):
        """
        Slash command for getting the current list of server boosters.

        Args:
            ctx (context.ApplicationContext): The context of the slash command.
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
    bot.add_cog(Boosters(bot))
    log.info("Commands loaded: boosters")
