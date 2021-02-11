import re
from datetime import datetime

def time_now() ->str:
    """ Returns current time in human-readable format. """
    now = datetime.utcnow
    time = now.strftime('%m/%d/%Y, %I:%M:%S %p')
    return (time)

def contains_link(ctx):
    regex = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    result = re.search(regex, ctx.content)
    return True if result else False


def has_attachment(ctx):
    return True if ctx.attachments else False
