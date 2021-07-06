import discord
from discord_slash import SlashContext


async def can_action_member(bot, ctx: SlashContext, member: discord.Member) -> bool:
    """ Stop mods from doing stupid things. """
    # Stop mods from actioning on the bot.
    if member.id == bot.user.id:
        return False

    # Stop mods from actioning one another, people higher ranked than them or themselves.
    if member.top_role >= ctx.author.top_role:
        return False

    # Checking if Bot is able to even perform the action
    if member.top_role >= member.guild.me.top_role:
        return False

    # Allow owner to override all limitations.
    if member.id == ctx.guild.owner_id:
        return True

    # Otherwise, the action is probably valid, return true.
    return True