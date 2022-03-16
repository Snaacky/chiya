import orjson
import re

import discord

from chiya import config, database
from chiya.utils import embeds

db = database.Database().get()
highlights = [
    dict(
        highlighted_term=highlight["highlighted_term"],
        subscribed_users=orjson.loads(highlight["subscribed_users"]),
    )
    for highlight in db["highlights"].find()
]
db.close()


def refresh_cache():
    db = database.Database().get()
    global highlights
    highlights = [
        dict(
            highlighted_term=highlight["highlighted_term"],
            subscribed_users=orjson.loads(highlight["subscribed_users"]),
        )
        for highlight in db["highlights"].find()
    ]

async def check_highlights(message: discord.Message):
    global highlights
    for highlight in highlights:
        regex = r"\b" + highlight['highlighted_term'] + r"\b"
        result = re.search(regex, message.clean_content, re.IGNORECASE)
        if result:
            # caught a term
            print("Caught a term!")
            embed = embeds.make_embed(
                title="Highlighted message caught!",
                description=f"[Message link]({message.jump_url})",
                color=discord.Color.gold()
            )
            for subscriber in highlight['subscribed_users']:
                member = message.guild.get_member(subscriber)
                if not member:
                    member = await message.guild.fetch_member(subscriber)
                try:
                    channel = await member.create_dm()
                    await channel.send(embed=embed)
                except:
                    pass
            
