import datetime
import re


def get_duration(duration):
    # Recycled RegEx from https://github.com/r-smashbros/setsudo/
    regex = r"((?:(\d+)\s*y(?:ears)?)?\s*(?:(\d+)\s*mo(?:nths)?)?\s*(?:(\d+)\s*w(?:eeks)?)?\s*(?:(\d+)\s*d(?:ays)?)?\s*(?:(\d+)\s*h(?:ours|rs|r)?)?\s*(?:(\d+)\s*m(?:inutes|in)?)?\s*(?:(\d+)\s*s(?:econds|ec)?)?)"

    # Attempt to parse the message argument with the Setsudo RegEx
    match_list = re.findall(regex, duration)[0]

    # Assign the arguments from the parsed message into variables.
    duration = dict(
        years=match_list[1],
        months=match_list[2],
        weeks=match_list[3],
        days=match_list[4],
        hours=match_list[5],
        minutes=match_list[6],
        seconds=match_list[7]
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
    end_time = datetime.datetime.timestamp(
        datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
            years=duration["years"],
            months=duration["months"],
            weeks=duration["weeks"],
            days=duration["days"],
            hours=duration["hours"],
            minutes=duration["minutes"],
            seconds=duration["seconds"]
        )
    )

    return duration_string, end_time
