import logging

import requests
from discord.commands import slash_command, context, Option
from discord.ext import commands, tasks

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)
trackers = ["AR", "BTN", "GGn", "PTP", "RED", "OPS"]


class TrackerStatusCommands(commands.Cog):
    # TODO: Add support for trackers that offer their own status page.
    # https://status.animebytes.tv/
    # http://about.empornium.ph/
    # https://status.myanonamouse.net/
    # http://is.morethantv.online/
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cache = {}
        self.refresh_data.start()

    def cog_unload(self) -> None:
        self.refresh_data.cancel()

    @tasks.loop(seconds=60)
    async def refresh_data(self):
        """
        Grabs the latest API data from trackerstatus.info and caches it locally
        every 60 seconds, respecting API limits.
        """
        for tracker in trackers:
            try:
                r = requests.get(url=f"https://{tracker}.trackerstatus.info/api/status/")
                r.raise_for_status()
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                log.error(e)
                pass

            if r.status_code == 200:
                self.cache[tracker] = r.json()

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

    @slash_command(guild_ids=config["guild_ids"], description="Get tracker uptime statuses", default_permission=True)
    async def trackerstatus(
        self,
        ctx: context.ApplicationContext,
        tracker: Option(
            str,
            description="Tracker to get uptime statuses for",
            choices=trackers,
            required=True
        )
    ) -> None:
        # TODO: Change the color of the embed to green if all services are online,
        # yellow if one of the services is offline, and grey or red if all are offline.
        await ctx.defer()

        embed = embeds.make_embed(
            ctx=ctx,
            title=f"Tracker Status: {tracker}",
        )

        for key, value in self.cache[tracker].items():
            # Skip over any keys that we don't want to return in the embed.
            if key in ["tweet", "TrackerHTTPAddresses", "TrackerHTTPSAddresses"]:
                continue
            embed.add_field(name=key, value=self.normalize_value(value), inline=True)

        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(TrackerStatusCommands(bot))
    log.info("Commands loaded: trackerstatus")
