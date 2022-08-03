import logging

from discord.commands import slash_command, context, Option
from discord.ext import commands, tasks

from chiya import config
from chiya.utils.trackerstatus import TrackerStatus, TrackerStatusAB, TrackerStatusInfo, TrackerStatusMAM


log = logging.getLogger(__name__)

trackers: list[TrackerStatus] = [
    TrackerStatusInfo("AR"),
    TrackerStatusInfo("BTN"),
    TrackerStatusInfo("GGn"),
    TrackerStatusInfo("PTP"),
    TrackerStatusInfo("RED"),
    TrackerStatusInfo("OPS"),
    TrackerStatusAB(),
    TrackerStatusMAM()
]
trackers_dict = {item.tracker: item for item in trackers}


class TrackerStatusCommands(commands.Cog):
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
        for tracker in trackers:
            tracker.do_refresh()

    @slash_command(guild_ids=config["guild_ids"], description="Get tracker uptime statuses")
    async def trackerstatus(
        self,
        ctx: context.ApplicationContext,
        tracker: Option(
            str,
            description="Tracker to get uptime statuses for",
            choices=sorted(list(trackers_dict.keys())),
            required=True
        ),
    ) -> None:
        # TODO: Change the color of the embed to green if all services are online,
        # yellow if one of the services is offline, and grey or red if all are offline.
        await ctx.defer()

        tracker: TrackerStatus = trackers_dict.get(tracker)
        embed = tracker.get_status_embed(ctx)

        await ctx.send_followup(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(TrackerStatusCommands(bot))
    log.info("Commands loaded: trackerstatus")
