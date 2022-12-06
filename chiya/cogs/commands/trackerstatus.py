import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from chiya import config
from chiya.utils.embeds import error_embed
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
trackers_list = sorted(list(trackers_dict.keys()))


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

    async def tracker_autocomplete(self, ctx: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=tracker, value=tracker)
            for tracker in trackers_list
            if current.lower() in tracker.lower()
        ]

    @app_commands.command(name="trackerstatus", description="Get tracker uptime statuses")
    @app_commands.guilds(config["guild_id"])
    @app_commands.autocomplete(tracker=tracker_autocomplete)
    @app_commands.describe(tracker="Tracker to get uptime statuses for")
    async def trackerstatus(
        self,
        ctx: discord.Interaction,
        tracker: str,
    ) -> None:
        # TODO: Change the color of the embed to green if all services are online,
        # yellow if one of the services is offline, and grey or red if all are offline.
        await ctx.response.defer()
        tracker: TrackerStatus = trackers_dict.get(tracker)

        if tracker is None:
            await ctx.followup.send(embed=error_embed(ctx, 'Please choose a listed tracker.'))
            return

        embed = tracker.get_status_embed(ctx)
        await ctx.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrackerStatusCommands(bot))
    log.info("Commands loaded: trackerstatus")
