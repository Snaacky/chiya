import datetime
import logging
import time

import discord
from discord.commands import Option, context, permissions, slash_command
from discord.ext import commands

import utils.duration
from utils import database, embeds
from utils.config import config
from utils.moderation import can_action_member


log = logging.getLogger(__name__)


class Restricts(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def is_user_restricted(self, ctx: context.ApplicationContext, member: discord.Member) -> bool:
        if discord.utils.get(ctx.guild.roles, id=config["roles"]["restricted"]) in member.roles:
            return True
        return False

    async def restrict_member(self, ctx: context.ApplicationContext, member: discord.Member, reason: str, end_time: float = None) -> None:
        await member.add_roles(discord.utils.get(ctx.guild.roles, id=config["roles"]["restricted"]), reason=reason)

        db = database.Database().get()
        db["mod_logs"].insert(dict(
            user_id=member.id,
            mod_id=ctx.author.id,
            timestamp=int(time.time()),
            reason=reason,
            type="restrict"
        ))

        if end_time:
            db["timed_mod_actions"].insert(dict(
                user_id=member.id,
                mod_id=ctx.author.id,
                action_type="restrict",
                reason=reason,
                start_time=datetime.datetime.now(tz=datetime.timezone.utc).timestamp(),
                end_time=end_time,
                is_done=False
            ))
        db.commit()
        db.close()

    async def unrestrict_member(self, member: discord.Member, reason: str, ctx: context.ApplicationContext = None) -> None:
        guild = ctx.guild if ctx else self.bot.get_guild(config["guild_id"])
        moderator = ctx.author if ctx else self.bot.user
        await member.remove_roles(discord.utils.get(guild.roles, id=config["roles"]["restricted"]), reason=reason)

        db = database.Database().get()
        db["mod_logs"].insert(dict(
            user_id=member.id,
            mod_id=moderator.id,
            timestamp=int(time.time()),
            reason=reason,
            type="unrestrict"
        ))

        entry = db["timed_mod_actions"].find_one(user_id=member.id, is_done=False)
        if entry:
            db["timed_mod_actions"].update(dict(id=entry["id"], is_done=True), ["id"])

        db.commit()
        db.close()

    async def send_restricted_dm_embed(self, ctx: context.ApplicationContext, member: discord.Member, reason: str = None, duration: str = None) -> bool:
        try:
            channel = await member.create_dm()
            embed = embeds.make_embed(
                author=False,
                title="Uh-oh, you've been restricted!",
                description="If you believe this was a mistake, contact staff.",
                color=0x8083b0
            )
            embed.add_field(name="Server:", value=f"[{ctx.guild}](https://discord.gg/piracy)", inline=True)
            embed.add_field(name="Moderator:", value=ctx.author.mention, inline=True)
            embed.add_field(name="Length:", value=duration or "Indefinite", inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/NlXwNqW.gif")
            return await channel.send(embed=embed)
        except discord.Forbidden:
            return False

    async def send_unrestricted_dm_embed(self, member: discord.Member, reason: str, ctx: context.ApplicationContext = None) -> bool:
        moderator = ctx.author if ctx else self.bot.user

        try:
            channel = await member.create_dm()
            embed = embeds.make_embed(
                author=False,
                title="Yay, you've been unrestricted!",
                description="Review our server rules to avoid being actioned again in the future.",
                color=0x8a3ac5
            )
            embed.add_field(name="Server:", value="[/r/animepiracy](https://discord.gg/piracy)", inline=True)
            embed.add_field(name="Moderator:", value=moderator.mention, inline=True)
            embed.add_field(name="Reason:", value=reason, inline=False)
            embed.set_image(url="https://i.imgur.com/rvvnpV2.gif")
            return await channel.send(embed=embed)
        except discord.Forbidden:
            return False

    @slash_command(guild_id=config["guild_id"], default_permission=False, description="Restricts message permissions from the member for the specified length of time")
    @permissions.has_role(config["roles"]["privileged"]["staff"])
    async def restrict(
        self,
        ctx: context.ApplicationContext,
        member: Option(discord.User, description="The member that will be restricted", required=True),
        reason: Option(str, description="The reason why the member is being restricted", required=True),
        duration: Option(str, description="The length of time the user will be restricted for", required=False),
    ):
        """ Temporarily restrict member in guild. """
        await ctx.defer()

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        if await self.is_user_restricted(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"{member.mention} is already restricted.")

        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        if duration:
            duration_string, restrict_end_time = utils.duration.get_duration(duration=duration)
        else:
            duration_string = restrict_end_time = None

        if duration and not duration_string:
            return await embeds.error_message(
                ctx=ctx,
                description=(
                    "Duration syntax: `#d#h#m#s` (day, hour, min, sec)\n"
                    "You can specify up to all four but you only need one."
                )
            )

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Restricting member: {member}",
            description=f"{member.mention} was restricted by {ctx.author.mention} for: {reason}",
            thumbnail_url="https://i.imgur.com/rHtYWIt.png",
            color="soft_red"
        )

        if duration:
            embed.add_field(name="Duration:", value=duration_string, inline=False)

        if not await self.send_restricted_dm_embed(ctx=ctx, member=member, reason=reason, duration=duration_string):
            embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                )
            )

        await self.restrict_member(ctx=ctx, member=member, reason=reason, end_time=restrict_end_time)
        return await ctx.respond(embed=embed)

    @slash_command(guild_id=config["guild_id"], default_permission=False, description="Unrestricts the member")
    @permissions.has_role(config["roles"]["privileged"]["staff"])
    async def unrestrict(
        self,
        ctx: context.ApplicationContext,
        member: Option(discord.User, description="The member that will be restricted", required=True),
        reason: Option(str, description="The reason why the member is being restricted", required=True),
    ):
        """ Unrestricts member in guild. """
        await ctx.defer()

        if not isinstance(member, discord.Member):
            return await embeds.error_message(ctx=ctx, description="That user is not in the server.")

        if not await can_action_member(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"You cannot action {member.mention}.")

        if not await self.is_user_restricted(ctx=ctx, member=member):
            return await embeds.error_message(ctx=ctx, description=f"{member.mention} is not restricted.")

        if len(reason) > 512:
            return await embeds.error_message(ctx=ctx, description="Reason must be less than 512 characters.")

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Unrestricting member: {member.name}",
            description=f"{member.mention} was unrestricted by {ctx.author.mention} for: {reason}",
            color="soft_green",
            thumbnail_url="https://i.imgur.com/W7DpUHC.png"
        )

        if not await self.send_unrestricted_dm_embed(ctx=ctx, member=member, reason=reason):
            embed.add_field(
                name="Notice:",
                value=(
                    f"Unable to message {member.mention} about this action. "
                    "This can be caused by the user not being in the server, "
                    "having DMs disabled, or having the bot blocked."
                )
            )

        await self.unrestrict_member(ctx=ctx, member=member, reason=reason)
        await ctx.respond(embed=embed)


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(Restricts(bot))
    log.info("Commands loaded: restricts")
