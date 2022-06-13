import datetime
import re
from typing import Tuple

import discord
from discord.commands import context

import logging

log = logging.getLogger(__name__)


async def can_action_member(ctx: context.ApplicationContext, member: discord.Member) -> bool:
    if member.bot:
        return False

    if member.top_role >= member.guild.me.top_role:
        return False

    if member.id == ctx.guild.owner_id:
        return True

    if ctx.author.top_role <= member.top_role:
        return False

    return True


def get_duration(duration) -> Tuple[str, float]:
    regex = (r"("
             r"(?:(\d+)\s*y(?:ears|ear|rs|r)?)?\s*"
             r"(?:(\d+)\s*mo(?:nths|nth)?)?\s*"
             r"(?:(\d+)\s*w(?:eeks|eek|ks|k)?)?\s*"
             r"(?:(\d+)\s*d(?:ays|ay)?)?\s*"
             r"(?:(\d+)\s*h(?:ours|our|rs|r)?)?\s*"
             r"(?:(\d+)\s*m(?:inutes|inute|ins|in)?)?\s*"
             r"(?:(\d+)\s*s(?:econds|econd|ecs|ec)?)?"
             r")"
             )

    match_list = re.findall(regex, duration)[0]

    duration = dict(
        years=match_list[1],
        months=match_list[2],
        weeks=match_list[3],
        days=match_list[4],
        hours=match_list[5],
        minutes=match_list[6],
        seconds=match_list[7],
    )

    for time_unit in duration:
        duration[time_unit] = float(duration[time_unit]) if duration[time_unit] != "" else 0

    duration["days"] += (duration["years"] * 365 + duration["months"] * 30)

    end_time = int(
        datetime.datetime.timestamp(
            datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(
                weeks=duration["weeks"],
                days=duration["days"],
                hours=duration["hours"],
                minutes=duration["minutes"],
                seconds=duration["seconds"],
            )
        )
    )

    return match_list, end_time
