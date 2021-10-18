import json
import re

import discord
from cogs.listeners.automod_message_updates import AutomodMessageUpdates
from discord.message import Message
from fuzzywuzzy import fuzz

from utils import database
from utils.config import config


def result_to_list(resultiter) -> list:
    final_list = list()
    for item in resultiter:
        final_list.append(dict(item))

    return final_list


# reading the config and setting up the values to be used in the future by automod
enabled_categories = config["automod"]["enabled_categories"]
disabled_channels = config["automod"]["disabled_channels"]
enabled_channels = config["automod"]["enabled_channels"]
excluded_roles = config["automod"]["excluded_roles"]
excluded_users = config["automod"]["excluded_users"]


# reading the database and setting up the values to be used in the future by automod
db = database.Database().get()
regex_censors = result_to_list(db["censor"].find(censor_type="regex"))
exact_censors = result_to_list(db["censor"].find(censor_type="exact"))
substring_censors = result_to_list(db["censor"].find(censor_type="substring"))
url_censors = result_to_list(db["censor"].find(censor_type="links"))
fuzzy_censors = result_to_list(db["censor"].find(censor_type="fuzzy"))
db.close()


async def check_message(message: discord.Message) -> bool:
    """Checks Messages for censors"""

    # Ignore the message if it's not from the automod-enabled channels/categories
    if not await is_in_enabled_channels(message):
        return False

    # excluding the message if the user's role has been excluded from automod
    for role in message.author.roles:
        if role.id in excluded_roles:
            return False

    # excluding the message if the user has been excluded from automod
    if message.author.id in excluded_users:
        return False

    for censor in regex_censors:
        if not censor["enabled"]:
            continue
        # Checking for exclusions for the particular term
        # json.loads() is used because the JSON List is stored as a string in the DB
        if is_user_excluded(
            message,
            json.loads(censor["excluded_users"]),
            json.loads(censor["excluded_roles"]),
        ):
            continue
        # regex checking
        if check_regex(message, censor["censor_term"]):
            await AutomodMessageUpdates.log_automodded_message(
                message, "Regex filter triggered."
            )
            return True

    for censor in exact_censors:
        if not censor["enabled"]:
            continue
        if is_user_excluded(
            message,
            json.loads(censor["excluded_users"]),
            json.loads(censor["excluded_roles"]),
        ):
            continue
        # regex checking the "exact" censor terms
        if check_exact(message, censor["censor_term"]):
            await AutomodMessageUpdates.log_automodded_message(
                message, "Exact filter triggered."
            )
            return True

    for censor in substring_censors:
        if not censor["enabled"]:
            continue
        if is_user_excluded(
            message,
            json.loads(censor["excluded_users"]),
            json.loads(censor["excluded_roles"]),
        ):
            continue
        # regex checking for substrings of the censor terms
        if check_substring(message, censor["censor_term"]):
            await AutomodMessageUpdates.log_automodded_message(
                message, "Substring filter triggered."
            )
            return True

    for censor in url_censors:
        if not censor["enabled"]:
            continue
        if is_user_excluded(
            message,
            json.loads(censor["excluded_users"]),
            json.loads(censor["excluded_roles"]),
        ):
            continue
        # regex checking for a URL matching ones read from the DB
        if check_substring(message, censor["censor_term"]):
            await AutomodMessageUpdates.log_automodded_message(
                message, "URL filter triggered."
            )
            return True

    for censor in fuzzy_censors:
        if not censor["enabled"]:
            continue
        if is_user_excluded(
            message,
            json.loads(censor["excluded_users"]),
            json.loads(censor["excluded_roles"]),
        ):
            continue
        # Doing a fuzzy matching with the word, with the specified threshold
        if check_fuzzy(message, censor["censor_term"], censor["censor_threshold"]):
            await AutomodMessageUpdates.log_automodded_message(
                message, "Fuzzy filter triggered."
            )
            return True

    # nothing matched
    return False


def is_user_excluded(
    message: discord.Message, excluded_users: list, excluded_roles: list
) -> bool:
    # Checking if the user is excluded from automod for that particular term
    author_id = message.author.id
    for role in message.author.roles:
        if excluded_roles:
            if role.id in excluded_roles:
                return True

    if excluded_users:
        if author_id in excluded_users:
            return True

    return False


def check_regex(message: Message, regex: str) -> bool:
    if re.search(regex, message.clean_content):
        return True
    return False


def check_exact(message: Message, term: str) -> bool:
    # exact and f-string wouldn't work on the same string, so concatenating.
    regex = r"\b" + term + r"\b"
    if re.search(regex, message.clean_content, re.IGNORECASE):
        return True
    return False


def check_substring(message: Message, term: str) -> bool:
    if re.search(term, message.clean_content, re.IGNORECASE):
        return True
    return False


def check_fuzzy(message: Message, term: str, threshold: int) -> bool:
    # partial ratio was found to be most suitable for this use-case
    # https://chairnerd.seatgeek.com/fuzzywuzzy-fuzzy-string-matching-in-python/
    if fuzz.partial_ratio(message.clean_content, term) >= threshold:
        return True
    return False


async def is_in_enabled_channels(message: discord.Message) -> bool:
    """Check if the sent message is from one of the enabled channels or not."""
    # if the channel category is enabled
    if message.channel.category_id in enabled_categories:
        # in case the channel the messagae was sent in was disabled
        if message.channel.id in disabled_channels:
            return False

        return True

    # in case a channel was specifically enabled for automod
    if message.channel.id in enabled_channels:
        return True

    return False


def refresh_censor_cache():
    """Refreshes the global censor cache."""
    db = database.Database().get()
    # declaring the variables as global, so that we're not modifying them in-place
    global regex_censors, exact_censors, substring_censors, url_censors, fuzzy_censors
    regex_censors = result_to_list(db["censor"].find(censor_type="regex"))
    exact_censors = result_to_list(db["censor"].find(censor_type="exact"))
    substring_censors = result_to_list(db["censor"].find(censor_type="substring"))
    url_censors = result_to_list(db["censor"].find(censor_type="links"))
    fuzzy_censors = result_to_list(db["censor"].find(censor_type="fuzzy"))
    db.close()
