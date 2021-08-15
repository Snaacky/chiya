import discord
from discord_slash import SlashContext

from cogs.commands import settings


async def can_action_member(bot, ctx: SlashContext, member: discord.Member) -> bool:
    """ Stop mods from doing stupid things. """
    # Stop mods from actioning on the bot.
    if member.id == bot.user.id:
        return False

    # Stop mods from actioning one another, people higher ranked than them or themselves.
    if member.top_role >= ctx.author.top_role:
        role_muted = discord.utils.get(member.guild.roles, id=settings.get_value("role_muted"))
        role_restricted = discord.utils.get(member.guild.roles, id=settings.get_value("role_restricted"))
        # Enable mods to use /unmute and /unrestrict on others since the role "Muted" and "Restricted" is placed higher than "Staff".
        if role_muted in member.roles or role_restricted in member.roles:
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
