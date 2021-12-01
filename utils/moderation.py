import discord
from discord_slash import SlashContext

from utils.config import config


async def can_action_member(ctx: SlashContext, member: discord.Member) -> bool:
    # Stop mods from actioning on the bot.
    if member.bot:
        return False

    # Stop mods from actioning one another, people higher ranked than them or themselves.
    if member.top_role >= ctx.author.top_role:
        muted = discord.utils.get(member.guild.roles, id=config["roles"]["muted"])
        restricted = discord.utils.get(member.guild.roles, id=config["roles"]["restricted"])
        # Enable mods to use /unmute and /unrestrict on others since the role "Muted" and "Restricted" is placed higher than "Staff".
        if muted in member.roles or restricted in member.roles:
            return True
        return False

    # Checking if Bot is able to even perform the action
    if member.top_role >= member.guild.me.top_role:
        return False

    # Allow owner to override all limitations.
    if member.id == ctx.guild.owner_id:
        return True

    # Otherwise, the action is probably valid, return true.
    return True
