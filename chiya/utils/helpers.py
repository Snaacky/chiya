import discord
from loguru import logger

from chiya.config import config


def can_action_member(ctx: discord.Interaction, member: discord.Member | discord.User) -> bool:
    # Pre-requisites for operation to run correctly.
    if not ctx.client.user or not ctx.guild:
        return False

    # Allow guild owner to override all limitations.
    if member.id == ctx.guild.owner_id:
        return True

    # Stop mods from actioning on the bot.
    if member.id == ctx.client.user.id:
        return False

    # Skip over the rest of the checks if it's a discord.User and not a discord.Member.
    if isinstance(member, discord.User):
        return True

    # Checking if bot is able to perform the action.
    if member.top_role >= member.guild.me.top_role:
        return False

    # Prevents mods from actioning other mods.
    if ctx.user.top_role <= member.top_role:
        return False

    return True


async def log_embed_to_channel(ctx: discord.Interaction, embed: discord.Embed) -> None:
    text_channels = ctx.guild.text_channels if ctx.guild else []

    moderation = discord.utils.get(text_channels, id=config.channels.moderation)
    chiya = discord.utils.get(text_channels, id=config.channels.chiya_log)

    if moderation:
        await moderation.send(embed=embed)
    else:
        logger.warning("Unable to log to moderation because it doesn't exist.")

    if chiya:
        await chiya.send(embed=embed)
    else:
        logger.warning("Unable to log to chiya because it doesn't exist.")
