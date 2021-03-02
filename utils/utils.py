import re


def contains_link(ctx):
    regex = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    result = re.search(regex, ctx.content)
    return True if result else False


def has_attachment(ctx):
    return True if ctx.attachments else False
