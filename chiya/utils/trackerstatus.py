import discord
import requests
import embeds
import logging

from discord.commands import context

log = logging.getLogger(__name__)

class TrackerStatus():
    def __init__(self, tracker:str) -> None:
        self.tracker = tracker

        self.cache_data = None

    def get_status_embed(self, ctx: context.ApplicationContext = None) -> discord.Embed:
        pass

    def do_refresh(self) -> None:
        pass


class TrackerStatusInfo(TrackerStatus):
    """
    Gets status of a tracker from trackerstatus.info
    """
    def __init__(self, tracker:str) -> None:
        super().__init__(tracker)

    def get_status_embed(self, ctx: context.ApplicationContext = None) -> discord.Embed:
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Tracker Status: {self.tracker}",
        )

        if self.cache_data is None:
            self.do_refresh()

        for key, value in self.cache_data.items():
            # Skip over any keys that we don't want to return in the embed.
            if key in ["tweet", "TrackerHTTPAddresses", "TrackerHTTPSAddresses"]:
                continue
            embed.add_field(name=key, value=self.normalize_value(value), inline=True)

        return embed

    def normalize_value(self, value):
        """
        Converts API data values into user-friendly text with status availability icon.
        """
        match value:
            case "1":
                return "<:status_online:596576749790429200> Online"
            case "2":
                return "<:status_dnd:596576774364856321> Unstable"
            case "0":
                return "<:status_offline:596576752013279242> Offline"

    def do_refresh(self) -> None:
        try:
            r = requests.get(url=f"https://{self.tracker}.trackerstatus.info/api/status/")
            r.raise_for_status()
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            log.error(e)
            pass

        if r.status_code == 200:
            self.cache_data = r.json()

class TrackerStatusAB(TrackerStatus):
    """
    Gets status of AB from API
    """
    URL = "https://status.animebytes.tv/api/status"

    def __init__(self) -> None:
        super().__init__("AB")

    def get_status_embed(self, ctx: context.ApplicationContext = None) -> discord.Embed:
        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Tracker Status: {self.tracker}",
        )

        if self.cache_data is None:
            self.do_refresh()

        if not self.cache_data.get("status", False):
            embed.set_footer("<:status_offline:596576752013279242> API Failed")

        for key, value in self.cache_data.get("status",{}).items():
            embed.add_field(name=key, value=self.normalize_value(value.get("status")), inline=True)

        return embed

    def normalize_value(self, value):
        """
        Converts API data values into user-friendly text with status availability icon.
        """
        match value:
            case 1:
                return "<:status_online:596576749790429200> Online"
            case 2:
                return "<:status_dnd:596576774364856321> Unstable"
            case 0:
                return "<:status_offline:596576752013279242> Offline"

    def do_refresh(self) -> None:
        try:
            r = requests.get(url=self.URL)
            r.raise_for_status()
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            log.error(e)
            pass

        if r.status_code == 200:
            self.cache_data: dict = r.json()

class TrackerStatusUptimeRobot(TrackerStatus):
    """
    Gets status of a tracker from trackerstatus.info
    """
    def __init__(self, tracker:str, url:str) -> None:
        self.url = url

        super().__init__(tracker)

    def get_status_embed(self, ctx: context.ApplicationContext = None) -> discord.Embed:
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


        return embed

    def normalize_value(self, value: dict):
        """
        Converts API data values into user-friendly text with status availability icon.
        """
        if value.get("label") == "success":
            return "<:status_online:596576749790429200> Online"
        ratio = float(value.get("ratio", "0"))
        if float(value.get("ratio")) > 95:
            return "<:status_dnd:596576774364856321> Unstable"
        elif ratio > 0:
            return "<:status_offline:596576752013279242> Offline"

        return "<:status_offline:596576752013279242> Unknown"

    def do_refresh(self) -> None:
        try:
            r = requests.get(url=self.url)
            r.raise_for_status()
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            log.error(e)
            pass

        if r.status_code == 200:
            self.cache_data: dict = r.json()

class TrackerStatusMAM(TrackerStatusUptimeRobot):
    def __init__(self) -> None:
        super().__init__("MAM", "https://status.myanonamouse.net/api/getMonitorList/vl59BTEJX")
