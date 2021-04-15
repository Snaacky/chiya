import logging

import discord

import config
from utils import embeds

log = logging.getLogger(__name__)


# Process whenver a new boost is received, regardless of previous boost status.
async def on_new_boost(before, after):
    if after.premium_subscription_count > before.premium_subscription_count:
        # Send an embed in the system channel thanking the user for boosting.
        embed = embeds.make_embed(author=False, color="nitro_pink")
        embed.title = f"A new booster appeared!"
        embed.description = f"""Thank you so much for the server boost! We are now at {after.premium_subscription_count} boosts!
        You can contact any <@&763031634379276308> member with a [hex color](https://www.google.com/search?q=hex+color) and your desired role name for a custom booster role."""
        embed.set_image(url="https://i.imgur.com/O8R98p9.gif")
        await before.system_channel.send(embed=embed)

        # Sent a log in #nitro-logs letting the staff know someone boosted with a link to a message near the boost.
        nitro_logs = discord.utils.get(after.guild.channels, id=config.nitro_logs)
        embed = embeds.make_embed(author=False, color="nitro_pink")
        last_message = await after.guild.system_channel.fetch_message(after.guild.system_channel.last_message_id)
        embed.description(f"[A new boost was added to the server.](https://canary.discord.com/channels/{after.guild.id}/{after.guild.system_channel.id}/{last_message.id})")
        await nitro_logs.send(embed=embed)

        # Log the boost to the console.
        log.info(f"A new boost was added to {after.guild.name}.")


# Proces when a user who previously hasn't boosted the server boosts.
async def process_new_booster(before, after):
    if before.premium_since is None and after.premium_since is not None:
        channel = discord.utils.get(after.guild.channels, id=config.nitro_logs)
        embed = embeds.make_embed(author=False, color="nitro_pink")
        embed.title = "New booster"
        embed.description = f"""{after.mention} boosted the server. We're now at {after.guild.premium_subscription_count} boosts."""
        await channel.send(embed=embed)

        log.info(f'{after.mention} boosted {after.guild.name}.')


# Process when a user who previously boosted the server removes all of their boosts from the server.
async def process_lost_booster(before, after):
    if before.premium_since is not None and after.premium_since is None:
        channel = discord.utils.get(after.guild.channels, id=config.nitro_logs)
        embed = embeds.make_embed(author=False, color="nitro_pink")
        embed.title = "Lost booster"
        embed.description = f"""{after.mention} no longer boosts the server. We're now at {after.guild.premium_subscription_count} boosts."""
        await channel.send(embed=embed)

        log.info(f'{after.mention} stopped boosting {after.guild.name}.')

