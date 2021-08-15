import logging

import discord

from cogs.commands import settings
from utils import embeds

log = logging.getLogger(__name__)


async def on_new_boost(before, after):
    """ 
    Process whenever a new boost is received.

    Parameters:
        before (discord.Guild): The guild prior to being updated.
        after  (discord.Guild): The guild after being updated.
        
    Called from:
        cogs/listeners/guild_updates.py: on_guild_update()
        
    """
    # TODO: Replace hardcoded mention with a .mention from settings.
    if after.premium_subscription_count > before.premium_subscription_count:
        # Send an embed in the system channel thanking the user for boosting.
        embed = embeds.make_embed(author=False, color="nitro_pink")
        embed.title = f"A new booster appeared!"
        embed.description = f"""Thank you so much for the server boost! We are now at {after.premium_subscription_count} boosts!
        You can contact any <@&763031634379276308> member with a [hex color](https://www.google.com/search?q=hex+color) and your desired role name for a custom booster role."""
        embed.set_image(url="https://i.imgur.com/O8R98p9.gif")
        await before.system_channel.send(embed=embed)

        # Send a embed in #nitro-logs that someone boosted with a link to a message near the boost.
        nitro_logs = discord.utils.get(after.channels, id=settings.get_value("channel_nitro_log"))
        embed = embeds.make_embed(author=False, color="nitro_pink")
        embed.description = f"[A new boost was added to the server.](https://canary.discord.com/channels/{after.id}/{after.system_channel.id}/{after.system_channel.last_message_id})"
        await nitro_logs.send(embed=embed)

        # Log the boost to the console.
        log.info(f"A new boost was added to {after.name}.")


async def on_removed_boost(before, after):
    """ 
    Process whenever a new boost is removed.

    Parameters:
        before (discord.Guild): The guild prior to being updated.
        after  (discord.Guild): The guild after being updated.
    
    Called from:
        cogs/listeners/guild_updates.py: on_guild_update()
    """
    if after.premium_subscription_count < before.premium_subscription_count:
        # Send an embed in #nitro-logs that someone removed a boost.
        nitro_logs = discord.utils.get(after.channels, id=settings.get_value("channel_nitro_log"))
        embed = embeds.make_embed(author=False, color="nitro_pink")
        embed.description = f"A boost was removed from the server."
        await nitro_logs.send(embed=embed)

        # Log the boost removal to the console.
        log.info(f"A boost was removed from {after.name}.")


async def process_new_booster(before, after):
    """ 
    Process when a user who previously hasn't boosted the server boosts.

    Parameters:
        before (discord.Member): The updated member’s old info.
        after  (discord.Member): The updated member’s updated info.
    
    Called from:
        cogs/listeners/member_updates.py: on_member_update()
    """
    # Send an embed in #nitro-logs that someone removed a boost.
    if not before.premium_since and after.premium_since:
        channel = discord.utils.get(after.guild.channels, id=settings.get_value("channel_nitro_log"))
        embed = embeds.make_embed(author=False, color="nitro_pink")
        embed.title = "New booster"
        embed.description = f"""{after.mention} boosted the server. We're now at {after.guild.premium_subscription_count} boosts."""
        await channel.send(embed=embed)

        # Log the boost removal to the console.
        log.info(f'{after} boosted {after.guild.name}.')


async def process_lost_booster(before, after):
    """ 
    Process when a user who previously boosted the server removes all of their boosts from the server.

    Parameters:
        before (discord.Member): The updated member’s old info.
        after  (discord.Member): The updated member’s updated info.
    
    Called from:
        cogs/listeners/member_updates.py: on_member_update()
    """
    # Send an embed in #nitro-logs that someone stopped boosting the server.
    if before.premium_since and not after.premium_since:
        channel = discord.utils.get(after.guild.channels, id=settings.get_value("channel_nitro_log"))
        embed = embeds.make_embed(author=False, color="nitro_pink")
        embed.title = "Lost booster"
        embed.description = f"""{after.mention} no longer boosts the server. We're now at {after.guild.premium_subscription_count} boosts."""
        await channel.send(embed=embed)

        # Log the booster removal to the console.
        log.info(f'{after} stopped boosting {after.guild.name}.')
