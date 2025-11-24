import time
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from loguru import logger

from chiya.config import config
from chiya.utils.embeds import error_embed


class TrackerStatus:
    def __init__(self, tracker: str, url: str) -> None:
        self.tracker = tracker
        self.cache_data: dict[str, Any] = {}
        self.url = url

    async def get_status_embed(self, ctx: discord.Interaction | None = None) -> discord.Embed:
        raise NotImplementedError

    async def do_refresh(self, session: aiohttp.ClientSession | None = None) -> None:
        try:
            session = session or aiohttp.ClientSession()
            async with session:
                async with session.get(self.url, timeout=aiohttp.ClientTimeout(10)) as response:
                    response.raise_for_status()
                    self.cache_data = await response.json()
        except Exception:
            logger.debug(f"Unable to refresh {self.tracker} tracker status")
            pass

    def get_embed_color(self, embed: discord.Embed) -> discord.Color:
        status = list(set([field.value for field in embed.fields]))
        if len(status) == 1:
            if status[0] == "🟢 Online":
                return discord.Color.green()
            elif status[0] == "🟠 Unstable":
                return discord.Color.orange()
            elif status[0] == "🔴 Offline":
                return discord.Color.red()
        else:
            if "🟢 Online" not in status:
                return discord.Color.red()
            else:
                return discord.Color.orange()

        return discord.Color.red()

    def normalize_value(self, value: Any) -> str | None:
        """
        Converts API data values into user-friendly text with status availability icon.
        """
        match value:
            case "1" | 1:
                return "🟢 Online"
            case "2" | 2:
                return "🟠 Unstable"
            case "0" | 0:
                return "🔴 Offline"


class TrackerStatusInfo(TrackerStatus):
    """
    Gets status of a tracker from trackerstatus.info
    """

    last_update = 0

    def __init__(self, tracker: str) -> None:
        super().__init__(tracker, "https://trackerstatus.info/api/list/")

    async def do_refresh(self, session: aiohttp.ClientSession | None = None) -> None:
        if time.time() - self.last_update > 10:
            await super().do_refresh(session)
            self.last_update = time.time()

    async def get_status_embed(self, ctx: discord.Interaction | None = None) -> discord.Embed:
        embed = discord.Embed()
        embed.title = f"Tracker Status: {self.tracker}"
        embed.color = self.get_embed_color(embed)

        if self.cache_data:
            self.last_update = 0
            await self.do_refresh()

        for key, value in self.cache_data[self.tracker.lower()]["Details"].items():
            # Skip over any keys that we don't want to return in the embed.
            if key in ["tweet", "TrackerHTTPAddresses", "TrackerHTTPSAddresses"]:
                continue
            embed.add_field(name=key, value=self.normalize_value(value), inline=True)

        return embed


class TrackerStatusAB(TrackerStatus):
    """
    Gets status of AB from API
    """

    def __init__(self) -> None:
        super().__init__("AB", "https://status.animebytes.tv/api/status")

    async def get_status_embed(self, ctx: discord.Interaction | None = None) -> discord.Embed:
        embed = discord.Embed()
        embed.title = f"Tracker Status: {self.tracker}"
        embed.color = self.get_embed_color(embed)

        if self.cache_data:
            await self.do_refresh()

        if not self.cache_data.get("status", False):
            embed.set_footer(text="🔴 API Failed")

        for key, value in self.cache_data.get("status", {}).items():
            embed.add_field(name=key, value=self.normalize_value(value.get("status")), inline=True)

        return embed


class TrackerStatusUptimeRobot(TrackerStatus):
    """
    Gets status of a tracker from trackerstatus.info
    """

    def __init__(self, tracker: str, url: str) -> None:
        super().__init__(tracker, url)

    async def get_status_embed(self, ctx: discord.Interaction | None = None) -> discord.Embed:
        embed = discord.Embed()
        embed.title = f"Tracker Status: {self.tracker}"
        embed.color = self.get_embed_color(embed)

        if self.cache_data:
            await self.do_refresh()

        monitors: list[dict] = self.cache_data.get("psp", {}).get("monitors", [])

        for monitor in monitors:
            dratio: dict = monitor.get("dailyRatios", [])[0]
            embed.add_field(name=monitor.get("name", "UNKNOWN"), value=self.normalize_value(dratio), inline=True)

        return embed

    def normalize_value(self, value: dict[str, Any]) -> str:
        """
        Converts API data values into user-friendly text with status availability icon.
        """
        if value.get("label") == "success":
            return "🟢 Online"
        ratio = float(value.get("ratio", "0"))
        if ratio > 95:
            return "🟠 Unstable"
        elif ratio > 0:
            return "🔴 Offline"
        return "🔴 Unknown"


class TrackerStatusMAM(TrackerStatusUptimeRobot):
    def __init__(self) -> None:
        super().__init__("MAM", "https://status.myanonamouse.net/api/getMonitorList/vl59BTEJX")


class TrackerStatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.refresh_data.start()

        self.trackers: tuple[TrackerStatus, ...] = (
            TrackerStatusInfo("AR"),
            TrackerStatusInfo("BTN"),
            TrackerStatusInfo("GGn"),
            TrackerStatusInfo("PTP"),
            TrackerStatusInfo("RED"),
            TrackerStatusInfo("OPS"),
            TrackerStatusInfo("NBL"),
            TrackerStatusAB(),
            TrackerStatusMAM(),
        )

        self.trackers_list = tuple(sorted((tracker.tracker for tracker in self.trackers)))

    async def cog_unload(self) -> None:
        self.refresh_data.cancel()

    @tasks.loop(seconds=60)
    async def refresh_data(self) -> None:
        """
        Grabs the latest API data from each tracker and caches it locally
        every 60 seconds, respecting API limits.
        """
        async with aiohttp.ClientSession() as session:
            for tracker in self.trackers:
                await tracker.do_refresh(session)

    async def tracker_autocomplete(self, ctx: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=tracker, value=tracker)
            for tracker in self.trackers_list
            if current.lower() in tracker.lower()
        ]

    @app_commands.command(name="trackerstatus", description="Get tracker uptime statuses")
    @app_commands.guilds(config.guild_id)
    @app_commands.autocomplete(tracker=tracker_autocomplete)
    @app_commands.describe(tracker="Tracker to get uptime statuses for")
    async def trackerstatus(self, ctx: discord.Interaction, tracker: str) -> None:
        await ctx.response.defer(ephemeral=True)

        tracker_status = next((tracker_e for tracker_e in self.trackers if tracker_e.tracker == tracker), None)

        if tracker_status is None:
            await ctx.followup.send(embed=error_embed(ctx, "Please choose a listed tracker."))
            return

        embed = await tracker_status.get_status_embed(ctx)
        await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrackerStatusCog(bot))
