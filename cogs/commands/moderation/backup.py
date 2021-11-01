import base64
import logging
import os
import time

import requests
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_permission

from utils import embeds
from utils.config import config
from utils.database import Database

log = logging.getLogger(__name__)


class PurgeCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    def url_to_base64(self, url: str):
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            return base64.b64encode(r.content)

    @cog_ext.cog_slash(
        # TODO: migrate to disnake for ctx.guild.stickers
        name="backup",
        description="Creates a backup of the server",
        guild_ids=[config["guild_id"]],
        default_permission=False,
        permissions={
            config["guild_id"]: [
                create_permission(config["roles"]["staff"], SlashCommandPermissionType.ROLE, True),
                create_permission(config["roles"]["trial_mod"], SlashCommandPermissionType.ROLE, True)
            ]
        }
    )
    async def backup(self, ctx: SlashContext):
        await ctx.defer()
        db_name = int(time.time())
        db = Database().get(f"sqlite:///{os.path.join(os.getcwd(), 'backups', f'{db_name}')}.db")

        log.info("Backing up guild settings and information")
        db["guild"].insert(dict(
            afk_timeout=ctx.guild.afk_timeout,
            banner=self.url_to_base64(str(ctx.guild.banner_url)),
            default_notifications=ctx.guild.default_notifications.value,
            explicit_content_filter=ctx.guild.explicit_content_filter.value,
            icon=self.url_to_base64(str(ctx.guild.icon_url)),
            mfa_level=ctx.guild.mfa_level,
            name=ctx.guild.name,
            region=ctx.guild.region.value,
            splash=self.url_to_base64(str(ctx.guild.splash_url)),
            verification_level=ctx.guild.verification_level.value
        ))

        log.info("Backing up bans list")
        bans = await ctx.guild.bans()
        for entry in bans:
            db["bans"].insert(dict(
                user=entry.user.id,
                reason=entry.reason
            ))

        log.info("Backing up emojis")
        emojis = await ctx.guild.fetch_emojis()
        for emoji in emojis:
            db["emojis"].insert(dict(
                name=emoji.name,
                image=self.url_to_base64(str(emoji.url))
            ))

        log.info("Backing up roles")
        roles = await ctx.guild.fetch_roles()
        for role in roles:
            db["roles"].insert(dict(
                hoisted=role.hoist,
                mentionable=role.mentionable,
                name=role.name,
                permissions=role.permissions.value,
                position=role.position,
                color=role.color.value
            ))
            # TODO: get role icon, probably disnake

        log.info("Backing up guild categories")
        for category in ctx.guild.categories:
            if category.id not in config["backup"]["skip_categories"]:
                db["categories"].insert(dict(
                    name=category.name,
                    nsfw=category.nsfw,
                    position=category.position,
                    permissions_synced=category.permissions_synced,
                    # TODO: get overwrites
                    # TODO: get members?
                    # TODO: get permissions?
                ))

        log.info("Backing up guild text channel information")
        for channel in ctx.guild.text_channels:
            if channel.id not in config["backup"]["skip_channels"]:
                db["text_channels"].insert(dict(
                    name=channel.name,
                    category=channel.category.name,
                    nsfw=channel.nsfw,
                    permissions_synced=channel.permissions_synced,
                    position=channel.position,
                    slowmode_delay=channel.slowmode_delay,
                    topic=channel.topic,
                    # TODO: get overwrites
                    # TODO: get members?
                    # TODO: get permissions?
                ))

        log.info("Backing up guild voice channel information")
        for channel in ctx.guild.voice_channels:
            if channel.id not in config["backup"]["skip_channels"]:
                db["voice_channels"].insert(dict(
                    name=channel.name,
                    bitrate=channel.bitrate,
                    category=channel.category.name,
                    permissions_synced=channel.permissions_synced,
                    position=channel.position,
                    user_limit=channel.user_limit
                    # TODO: get overwrites
                    # TODO: get members?
                    # TODO: get permissions?
                ))

        # TODO: get message history
        log.info(f"Backing up created, stored as backups/{db_name}.db")
        await ctx.send("done")


def setup(bot: Bot) -> None:
    bot.add_cog(PurgeCog(bot))
    log.info("Commands loaded: purge")
