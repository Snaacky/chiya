import discord
import re
import dataset
import json

from utils import database
from fuzzywuzzy import fuzz
from cogs.commands import settings


async def check_message(message: discord.Message) -> bool:
    """ Checks Messages by calling various other methods. """

    # Ignore the message if it's not from the automod-enabled channels/categories
    if not await is_in_enabled_channels(message):
        return False

    
    db = dataset.connect(database.get_db())
    # querying everything from the database
    regex_censors = db['censor'].find(censor_type="regex")
    for censor in regex_censors:
        if not censor['enabled']:
            continue
        if is_user_excluded(message, json.loads(censor['excluded_users']), json.loads(censor['excluded_roles'])):
            continue
        # regex checking
        if check_regex(message.content, censor['censor_term']):
            return True
    
    exact_censors = db['censor'].find(censor_type="exact")
    for censor in exact_censors:
        if not censor['enabled']:
            continue
        if is_user_excluded(message, json.loads(censor['excluded_users']), json.loads(censor['excluded_roles'])):
            continue
        # regex checking the "exact" censor terms
        if check_exact(message.content, censor['censor_term']):
            return True
    
    substring_censors = db['censor'].find(censor_type="substring")
    for censor in substring_censors:
        if not censor['enabled']:
            continue
        if is_user_excluded(message, json.loads(censor['excluded_users']), json.loads(censor['excluded_roles'])):
            continue
        # regex checking for substrings of the censor terms
        if check_substring(message.content, censor['censor_term']):
            return True
        
    url_censors = db['censor'].find(censor_type="links")
    for censor in url_censors:
        if not censor['enabled']:
            continue
        if is_user_excluded(message, json.loads(censor['excluded_users']), json.loads(censor['excluded_roles'])):
            continue
        # regex checking for a URL matching ones read from the DB
        if check_substring(message.content, censor['censor_term']):
            return True
    
    fuzzy_censors = db['censor'].find(censor_type="fuzzy")
    for censor in fuzzy_censors:
        if not censor['enabled']:
            continue
        if is_user_excluded(message, json.loads(censor['excluded_users']), json.loads(censor['excluded_roles'])):
            continue
        # Doing a fuzzy matching with the word, with the specified threshold
        if check_fuzzy(message.content, censor['censor_term'], censor['censor_threshold']):
            return True
    
    db.close()
    # nothing matched
    return False

def is_user_excluded(message: discord.Message, excluded_users: list, excluded_roles: list) -> bool:
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
    

def check_regex(message: str, regex: str) -> bool:
    if re.search(regex, message):
        return True
    return False

def check_exact(message: str, term: str) -> bool:
    regex = r"\b" +term+ r"\b"
    if re.search(regex, message, re.IGNORECASE):
        return True
    return False


def check_substring(message: str, term: str) -> bool:
    if re.search(term, message, re.IGNORECASE):
        return True
    return False

def check_fuzzy(message: str, term: str, threshold: int) -> bool:
    if(fuzz.partial_ratio(message, term) >= threshold):
        return True
    return False

async def is_in_enabled_channels(message: discord.Message) -> bool:
        """ Check if the sent message is from one of the enabled channels or not. """
        # Get all categories from the guild.
        categories = message.guild.categories
        # Return true if the message was sent any channel under the community category.
        if any(message.channel.category.id == settings.get_value("category_community") for category in categories):
            return True
        # Return true if the message was sent any channel under the bots category.
        if any(message.channel.category.id == settings.get_value("category_bots") for category in categories):
            return True
        # Return true if the message was sent any channel under the voice category.
        if any(message.channel.category.id == settings.get_value("category_voice") for category in categories):
            return True
        return False

