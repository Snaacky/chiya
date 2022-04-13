import logging

import discord
from discord.commands import Option, context, permissions, slash_command
from discord.ext import commands

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class GeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @slash_command(
        guild_ids=config["guild_ids"], description="Gets a users profile picture"
    )
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
        if isinstance(user, int):
            user = await self.bot.fetch_user(user)

        embed = embeds.make_embed()
        if server and user.guild_avatar is not None:
            embed.set_author(icon_url=user.guild_avatar.url, name=str(user))
            embed.set_image(url=user.guild_avatar.url)
        elif server and user.guild_avatar is None:
            embed.set_author(icon_url=user.avatar.url, name=str(user))
            embed.set_image(url=user.avatar.url)
            embed.set_footer(
                text="⚠️ Prefer server profile picture was specified but user does not have a server profile picture set."
            )
        else:
            embed.set_author(icon_url=user.avatar.url, name=str(user))
            embed.set_image(url=user.avatar.url)
        await ctx.send_followup(embed=embed)

    @slash_command(
        guild_ids=config["guild_ids"],
        default_permission=False,
        description="Add vote reactions to a message.",
    )
    @permissions.has_role(config["roles"]["staff"])
    async def vote(
        self,
        ctx: context.ApplicationContext,
        message: Option(
            str, description="The ID for the target message", required=False
        ),
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
                return await embeds.error_message(
                    ctx=ctx, description="Invalid message ID."
                )

        if not message:
            messages = await ctx.channel.history(limit=1).flatten()
            message = messages[0]

        # TODO: replace this with emotes grabbed from config
        await message.add_reaction(":yes:914162499023142996")
        await message.add_reaction(":no:914162576403873832")
        await embeds.success_message(
            ctx=ctx, description=f"Added votes to {message.jump_url}"
        )

    @slash_command(
        guild_ids=config["guild_ids"],
        default_permission=False,
        description="Summarises a vote, and displays results.",
    )
    @permissions.has_role(config["roles"]["staff"])
    async def vote_info(
        self,
        ctx: context.ApplicationContext,
        message: Option(
            str, description="The ID for the target message", required=True
        ),
    ) -> None:
        """
        Summarises a vote, and displays results.
        """
        await ctx.defer()

        if message:
            try:
                message = await ctx.channel.fetch_message(message)
            except discord.NotFound:
                return await embeds.error_message(
                    ctx=ctx, description="Invalid message ID."
                )

        yes_reactions = None
        no_reactions = None
        
        for reaction in message.reactions:
            if reaction.emoji.id == 914162499023142996:
                yes_reactions = reaction
            if reaction.emoji.id == 914162576403873832:
                no_reactions = reaction

        if not yes_reactions or not no_reactions:
            return await embeds.error_message(
                ctx=ctx,
                description="That message does not have the appropriate yes and no reactions.",
            )

        yes_users = []
        async for user in yes_reactions.users():
            if not user.bot:
                yes_users.append(user.mention)

        no_users = []
        async for user in no_reactions.users():
            if not user.bot:
                no_users.append(user.mention)

        both_users = set(yes_users).intersection(set(no_users))

        staff = discord.utils.get(message.guild.roles, id=config['roles']['staff']).members
        staff_users = []
        for user in staff:
            if not user.bot:
                staff_users.append(user.mention)

        skipped_users = set(staff_users).difference(
            set(yes_users).union(set(no_users))
        )

        embed = embeds.make_embed(
            ctx=ctx, author=True, title="Results of vote", 
            description=f"""<:yes:914162499023142996> - **{len(yes_users)}** {" ".join(yes_users)}
            <:no:914162576403873832> - **{len(no_users)}** {" ".join(no_users)}
            **Both: ** **{len(both_users)}** {" ".join(both_users)}
            **Did not vote: ** **{len(skipped_users)}** {" ".join(skipped_users)}
            """, color=discord.Color.green()
        )

        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(GeneralCommands(bot))
    log.info("Commands loaded: general")

