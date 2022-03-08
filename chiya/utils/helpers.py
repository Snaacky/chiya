import datetime
import re
from typing import Tuple

import discord
from discord.commands import context

import logging


log = logging.getLogger(__name__)


async def can_action_member(ctx: context.ApplicationContext, member: discord.Member) -> bool:
    # Stop mods from actioning on the bot.
    if member.bot:
        return False

    # Checking if bot is able to perform the action
    if member.top_role >= member.guild.me.top_role:
        return False

    # Allow owner to override all limitations.
    if member.id == ctx.guild.owner_id:
        return True

    # Otherwise, the action is probably valid, return true.
    return True


def get_duration(duration) -> Tuple[str, float]:
    # Recycled RegEx from https://github.com/r-smashbros/setsudo/
    regex = r"((?:(\d+)\s*w(?:eeks|eek|ks|k)?)?\s*(?:(\d+)\s*d(?:ays|ay)?)?\s*(?:(\d+)\s*h(?:ours|our|rs|r)?)?\s*(?:(\d+)\s*m(?:inutes|inute|ins|in)?)?\s*(?:(\d+)\s*s(?:econds|econd|ecs|ec)?)?)"

    # Attempt to parse the message argument with the Setsudo RegEx
    match_list = re.findall(regex, duration)[0]

    # Assign the arguments from the parsed message into variables.
    duration = dict(
        weeks=match_list[1],
        days=match_list[2],
        hours=match_list[3],
        minutes=match_list[4],
        seconds=match_list[5],
    )

    # String that will store the duration in a more digestible format.
    duration_string = ""
    for time_unit in duration:
        # If the time value is undeclared, set it to 0 and skip it.
        if duration[time_unit] == "":
            duration[time_unit] = 0
            continue
        # If the time value is 1, make the time unit into singular form.
        if duration[time_unit] == "1":
            duration_string += f"{duration[time_unit]} {time_unit[:-1]} "
        else:
            duration_string += f"{duration[time_unit]} {time_unit} "
        # Updating the values for ease of conversion to timedelta object later.
        duration[time_unit] = float(duration[time_unit])

    # Adds the timedelta of the ban length to the current time to get the mod command end datetime.
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

    return duration_string, end_time
