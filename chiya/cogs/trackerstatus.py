import time
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from loguru import logger

from chiya.config import config
from chiya.utils import embeds
from chiya.utils.embeds import error_embed


class TrackerStatus:
    def __init__(self, tracker: str, url: str) -> None:
        self.tracker = tracker
        self.cache_data: dict = None
        self.url = url

    def get_status_embed(self, ctx: discord.Interaction = None) -> discord.Embed:
        pass

    async def do_refresh(self, session: aiohttp.ClientSession) -> None:
        try:
            async with session.get(self.url, timeout=10) as response:
                response.raise_for_status()
                self.cache_data = await response.json()
        except Exception:
            logger.debug(f"Unable to refresh {self.tracker} tracker status")
            pass

    def get_embed_color(self, embed: discord.Embed):
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


class TrackerStatusInfo(TrackerStatus):
    """
    Gets status of a tracker from trackerstatus.info
    """

    last_update = 0
    global_data: dict = None

    def __init__(self, tracker: str) -> None:
        super().__init__(tracker, "https://trackerstatus.info/api/list/")

    async def do_refresh(self, session: aiohttp.ClientSession) -> None:
        if time.time() - self.last_update > 10:
            await super().do_refresh(session)
            self.global_data = self.cache_data
            self.last_update = time.time()

    def get_status_embed(self, ctx: discord.Interaction = None) -> discord.Embed:
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Tracker Status: {self.tracker}",
        )

        if self.global_data is None:
            self.last_update = 0
            self.do_refresh()

        for key, value in self.global_data[self.tracker.lower()]["Details"].items():
            # Skip over any keys that we don't want to return in the embed.
            if key in ["tweet", "TrackerHTTPAddresses", "TrackerHTTPSAddresses"]:
                continue
            embed.add_field(name=key, value=self.normalize_value(value), inline=True)

        embed.color = self.get_embed_color(embed)

        return embed


def normalize_value(self, value):
    """
    Converts API data values into user-friendly text with status availability icon.
    """
    match value:
        case "1":
            return "🟢 Online"
        case "2":
            return "🟠 Unstable"
        case "0":
            return "🔴 Offline"


class TrackerStatusAB(TrackerStatus):
    """
    Gets status of AB from API
    """

    def __init__(self) -> None:
        super().__init__("AB", "https://status.animebytes.tv/api/status")

    def get_status_embed(self, ctx: discord.Interaction = None) -> discord.Embed:
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Tracker Status: {self.tracker}",
        )

        if self.cache_data is None:
            self.do_refresh()

        if not self.cache_data.get("status", False):
            embed.set_footer("🔴 API Failed")

        for key, value in self.cache_data.get("status", {}).items():
            embed.add_field(name=key, value=self.normalize_value(value.get("status")), inline=True)

        embed.color = self.get_embed_color(embed)

        return embed

    def normalize_value(self, value):
        """
        Converts API data values into user-friendly text with status availability icon.
        """
        match value:
            case 1:
                return "🟢 Online"
            case 2:
                return "🟠 Unstable"
            case 0:
                return "🔴 Offline"


class TrackerStatusUptimeRobot(TrackerStatus):
    """
    Gets status of a tracker from trackerstatus.info
    """

    def __init__(self, tracker: str, url: str) -> None:
        super().__init__(tracker, url)

    def get_status_embed(self, ctx: discord.Interaction = None) -> discord.Embed:
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Tracker Status: {self.tracker}",
        )

        if self.cache_data is None:
            self.do_refresh()

        monitors: list[dict] = self.cache_data.get("psp", {}).get("monitors", [])

        for monitor in monitors:
            dratio: dict = monitor.get("dailyRatios", [])[0]
            embed.add_field(name=monitor.get("name", "UNKNOWN"), value=self.normalize_value(dratio), inline=True)

        embed.color = self.get_embed_color(embed)

        return embed

    def normalize_value(self, value: dict):
        """
        Converts API data values into user-friendly text with status availability icon.
        """
        if value.get("label") == "success":
            return "🟢 Online"
        ratio = float(value.get("ratio", "0"))
        if float(value.get("ratio")) > 95:
            return "🟠 Unstable"
        elif ratio > 0:
            return "🔴 Offline"
        return "🔴 Unknown"


class TrackerStatusMAM(TrackerStatusUptimeRobot):
    def __init__(self) -> None:
        super().__init__("MAM", "https://status.myanonamouse.net/api/getMonitorList/vl59BTEJX")


trackers: list[TrackerStatus] = [
    TrackerStatusInfo("AR"),
    TrackerStatusInfo("BTN"),
    TrackerStatusInfo("GGn"),
    TrackerStatusInfo("PTP"),
    TrackerStatusInfo("RED"),
    TrackerStatusInfo("OPS"),
    TrackerStatusInfo("NBL"),
    TrackerStatusAB(),
    TrackerStatusMAM(),
]
trackers_dict = {item.tracker: item for item in trackers}
trackers_list = sorted(list(trackers_dict.keys()))


class TrackerStatusCog(commands.Cog):
    # TODO: Add support for trackers that offer their own status page.
    # http://about.empornium.ph/
    # http://is.morethantv.online/
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.refresh_data.start()

    def cog_unload(self) -> None:
        self.refresh_data.cancel()

    @tasks.loop(seconds=60)
    async def refresh_data(self):
        """
        Grabs the latest API data from trackerstatus.info and caches it locally
        every 60 seconds, respecting API limits.
        """
        async with aiohttp.ClientSession() as session:
            for tracker in trackers:
                await tracker.do_refresh(session)

    async def tracker_autocomplete(self, ctx: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=tracker, value=tracker)
            for tracker in trackers_list
            if current.lower() in tracker.lower()
        ]

    @app_commands.command(name="trackerstatus", description="Get tracker uptime statuses")
    @app_commands.guilds(config.guild_id)
    @app_commands.autocomplete(tracker=tracker_autocomplete)
    @app_commands.describe(tracker="Tracker to get uptime statuses for")
    async def trackerstatus(
        self,
        ctx: discord.Interaction,
        tracker: str,
    ) -> None:
        # TODO: Change the color of the embed to green if all services are online,
        # yellow if one of the services is offline, and grey or red if all are offline.
        await ctx.response.defer(ephemeral=True)
        tracker: TrackerStatus = trackers_dict.get(tracker)

        if tracker is None:
            await ctx.followup.send(embed=error_embed(ctx, "Please choose a listed tracker."))
            return

        embed = tracker.get_status_embed(ctx)
        await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrackerStatusCog(bot))
