import discord
import re
import dataset
from utils import database
from fuzzywuzzy import fuzz


def check_message(message: discord.Message) -> bool:
    """ Checks Messages by calling various other methods. """
    with dataset.connect(database.get_db()) as db:
        statement = "SELECT * FROM censor WHERE censor_type=\'regex\'"
        result = db.query(statement)
        for x in result:
            # regex checking
            if(check_regex(message.content, result['censor_term'])):
                return True
        
        statement = "SELECT * from censor WHERE censor_type=\'exact\'"
        result = db.query(statement)
        for x in result:
            # exact word matching
            if(check_exact(message.content, x['censor_term'])):
                return True
        
        statement = "SELECT * from censor WHERE censor_type=\'substring\'"
        result = db.query(statement)
        for x in result:
            # substring matching
            if(check_substring(message.content, x['censor_term'])):
                return True

        statement = "SELECT * from censor WHERE censor_type=\'url\'"
        result = db.query(statement)
        for x in result:
            # exact word matching
            if(check_url(message.content, x['censor_term'])):
                return True
    
        statement = "SELECT * from censor WHERE censor_type=\'fuzzy\'"
        result = db.query(statement)
        for x in result:
            # exact word matching
            if(check_fuzzy(message.content, x['censor_term'])):
                return True

    # nothing matched :(
    return False

def check_regex(message: str, regex: str) -> bool:
    """ Regex checking. """
    
    if re.search(regex, message):
        return True
    
    return False


def check_exact(message: str, term: str) -> bool:
    """ Exact checking. """
    regex = r"\b" +term+ r"\b"
    if re.search(regex, message, re.IGNORECASE):
        return True
   
    return False


def check_substring(message: str, term: str) -> bool:
    """ Substring checking. """
    if re.search(term, message, re.IGNORECASE):
        return True
    
    return False


def check_fuzzy(message: str, term: str) -> bool:
    """ Fuzzy checking """
    return False

def check_url(message: str, term: str) -> bool:
    """ URL checking """
    return False
