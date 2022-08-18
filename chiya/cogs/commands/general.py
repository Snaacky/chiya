import logging

import discord
from discord import app_commands
from discord.ext import commands

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class GeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="pfp", description="Gets a users profile picture")
    @app_commands.guilds(config["guild_id"])
    @app_commands.describe(user="User whose profile picture will be grabbed2")
    @app_commands.describe(profile="Prefer global profile picture3")
    async def pfp(
        self,
        ctx: discord.Interaction,
        user: discord.Member | discord.User,
        profile: bool
    ) -> None:
        """
        Grab a user's avatar and return it in a large-sized embed.

        If the user parameter is not specified, the function will grab the
        invokers avatar instead. Offers the ability to attempt to grab a users
        server avatar and will fallback to their global avatar with a warning
        attached if a server specific avatar is not set.
        """
        await ctx.response.defer(thinking=True)

        user = user or ctx.author

        embed = embeds.make_embed()
        if profile and isinstance(user, discord.Member):
            user: discord.User = ctx.bot.get_user(user.id)

        embed.set_author(icon_url=user.display_avatar.url, name=str(user))
        embed.set_image(url=user.display_avatar.url)
        await ctx.followup.send(embed=embed)

    # @slash_command(
    #     guild_ids=config["guild_ids"],
    #     description="Summarises a vote, and displays results.",
    # )
    # @commands.has_role(config["roles"]["staff"])
    # async def vote_info(
    #     self,
    #     ctx: context.ApplicationContext,
    #     message: Option(str, description="The ID for the target message", required=True),
    # ) -> None:
    #     """
    #     Summarises a vote, and displays results.
    #     """
    #     await ctx.defer()
# 
    #     if message:
    #         try:
    #             message: discord.Message = await ctx.channel.fetch_message(message)
    #         except discord.NotFound:
    #             return await embeds.error_message(ctx=ctx, description="Invalid message ID.")
# 
    #     yes_reactions = None
    #     no_reactions = None
# 
    #     emoji_yes = discord.utils.get(ctx.guild.emojis, id=config['emoji']['yes']) or "👍"
    #     emoji_no = discord.utils.get(ctx.guild.emojis, id=config['emoji']['no']) or "👎" 
# 
    #     for reaction in message.reactions:
    #         if reaction.emoji == emoji_yes:
    #             yes_reactions = reaction
    #         if reaction.emoji == emoji_no:
    #             no_reactions = reaction
# 
    #     if not yes_reactions or not no_reactions:
    #         return await embeds.error_message(
    #             ctx=ctx,
    #             description="That message does not have the appropriate yes and no reactions.",
    #         )
# 
    #     yes_users = set(await yes_reactions.users().flatten())
    #     no_users = set(await no_reactions.users().flatten())
    #     both_users = yes_users.intersection(no_users)
    #     role_staff = discord.utils.get(message.guild.roles, id=config["roles"]["staff"])
    #     staff_users = set(user for user in role_staff.members)
    #     skipped_users = staff_users.difference(yes_users.union(no_users))
# 
    #     yes_users = [user.mention if not user.bot else "" for user in yes_users.copy()]
    #     no_users = [user.mention if not user.bot else "" for user in no_users.copy()]
    #     both_users = [user.mention if not user.bot else "" for user in both_users.copy()]
    #     skipped_users = [user.mention if not user.bot else "" for user in skipped_users.copy()]
# 
    #     embed = embeds.make_embed(
    #         ctx=ctx,
    #         author=True,
    #         title="Results of vote",
    #         description=f"""<:yes:{config['emoji']['yes']}> - **{len(yes_users) - 1}** {" ".join(yes_users)}
    #         <:no:{config['emoji']['no']}> - **{len(no_users) - 1}** {" ".join(no_users)}
    #         **Both: ** **{len(both_users) - 1}** {" ".join(both_users)}
    #         **Did not vote: ** **{len(skipped_users)}** {" ".join(skipped_users)}
    #         """,
    #         color=discord.Color.green(),
    #     )
# 
    #     await ctx.send_followup(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GeneralCommands(bot))
    log.info("Commands loaded: general")
