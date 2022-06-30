import logging

import discord
from chiya import config
from chiya.utils import embeds
from discord.commands import Option, context, slash_command
from discord.ext import commands

log = logging.getLogger(__name__)


class GeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @slash_command(guild_ids=config["guild_ids"], description="Gets a users profile picture")
    async def pfp(
        self,
        ctx: context.ApplicationContext,
        user: Option(
            discord.User,
            description="User whose profile picture will be grabbed",
            required=False,
        ),
        server: Option(
            bool,
            description="Prefer server profile picture (if one exists)",
            required=False,
        ),
    ) -> None:
        """
        Grab a user's avatar and return it in a large-sized embed.

        If the user parameter is not specified, the function will grab the
        invokers avatar instead. Offers the ability to attempt to grab a users
        server avatar and will fallback to their global avatar with a warning
        attached if a server specific avatar is not set.
        """
        await ctx.defer()

        user = user or ctx.author
        user = await ctx.guild.fetch_member(user.id)
        
        embed = embeds.make_embed()
        if server and user.guild_avatar is not None:
            embed.set_author(icon_url=user.guild_avatar.url, name=str(user))
            embed.set_image(url=user.guild_avatar.url)
        elif server and user.guild_avatar is None:
            embed.set_author(icon_url=user.display_avatar, name=str(user))
            embed.set_image(url=user.display_avatar)
            embed.set_footer(
                text="⚠️ Prefer server profile picture was specified but user does not have a server profile picture set."
            )
        else:
            embed.set_author(icon_url=user.display_avatar, name=str(user))
            embed.set_image(url=user.display_avatar)
        await ctx.send_followup(embed=embed)

    @slash_command(
        guild_ids=config["guild_ids"],
        description="Add vote reactions to a message.",
    )
    @commands.has_role(config["roles"]["staff"])
    async def vote(
        self,
        ctx: context.ApplicationContext,
        message: Option(str, description="The ID for the target message", required=False),
    ) -> None:
        """
        Adds vote emojis (yes and no) reactions to a message.

        If the message argument is specified, it will add the reactions to
        that message. Otherwise, it will add the reactions to the last message
        in the channel.
        """
        # TODO: what happens if the user doesn't have permission to add reactions in that channel?
        await ctx.defer(ephemeral=True)

        if message:
            try:
                message = await ctx.channel.fetch_message(message)
            except discord.NotFound:
                return await embeds.error_message(ctx=ctx, description="Invalid message ID.")

        if not message:
            messages = await ctx.channel.history(limit=1).flatten()
            message = messages[0]

        await message.add_reaction(f":yes:{config['emoji']['yes']}")
        await message.add_reaction(f":no:{config['emoji']['no']}")
        await embeds.success_message(ctx=ctx, description=f"Added votes to {message.jump_url}")

    @slash_command(
        guild_ids=config["guild_ids"],
        description="Summarises a vote, and displays results.",
    )
    @commands.has_role(config["roles"]["staff"])
    async def vote_info(
        self,
        ctx: context.ApplicationContext,
        message: Option(str, description="The ID for the target message", required=True),
    ) -> None:
        """
        Summarises a vote, and displays results.
        """
        await ctx.defer()

        if message:
            try:
                message = await ctx.channel.fetch_message(message)
            except discord.NotFound:
                return await embeds.error_message(ctx=ctx, description="Invalid message ID.")

        yes_reactions = None
        no_reactions = None

        for reaction in message.reactions:
            if reaction.emoji.id == config["emoji"]["yes"]:
                yes_reactions = reaction
            if reaction.emoji.id == config["emoji"]["no"]:
                no_reactions = reaction

        if not yes_reactions or not no_reactions:
            return await embeds.error_message(
                ctx=ctx,
                description="That message does not have the appropriate yes and no reactions.",
            )

        yes_users = set(await yes_reactions.users().flatten())
        no_users = set(await no_reactions.users().flatten())
        both_users = yes_users.intersection(no_users)
        role_staff = discord.utils.get(message.guild.roles, id=config["roles"]["staff"])
        staff_users = set(user for user in role_staff.members)
        skipped_users = staff_users.difference(yes_users.union(no_users))

        yes_users = [user.mention if not user.bot else "" for user in yes_users.copy()]
        no_users = [user.mention if not user.bot else "" for user in no_users.copy()]
        both_users = [user.mention if not user.bot else "" for user in both_users.copy()]
        skipped_users = [user.mention if not user.bot else "" for user in skipped_users.copy()]

        embed = embeds.make_embed(
            ctx=ctx,
            author=True,
            title="Results of vote",
            description=f"""<:yes:{config['emoji']['yes']}> - **{len(yes_users) - 1}** {" ".join(yes_users)}
            <:no:{config['emoji']['no']}> - **{len(no_users) - 1}** {" ".join(no_users)}
            **Both: ** **{len(both_users) - 1}** {" ".join(both_users)}
            **Did not vote: ** **{len(skipped_users)}** {" ".join(skipped_users)}
            """,
            color=discord.Color.green(),
        )

        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(GeneralCommands(bot))
    log.info("Commands loaded: general")
