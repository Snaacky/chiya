import asyncio
import discord
import logging
import praw
import time
import traceback
from discord.ext import commands
import config

logging.basicConfig(
    filename="output.log",
    filemode='a',
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)
logging.getLogger().addHandler(logging.StreamHandler())

reddit = praw.Reddit(
    client_id=config.REDDIT_API_CLIENT_ID,
    client_secret=config.REDDIT_API_CLIENT_SECRET,
    user_agent=f"Chiya (for /r/{config.SUBREDDIT_NAME})"
)

subreddit = config.SUBREDDIT_NAME


async def check_for_posts(bot):
    await bot.wait_until_ready()
    bot_started_at = time.time()
    logging.info(f"Logged into Discord as user: {bot.user.name}.")
    cache = []

    while True:
        try:
            for submission in reddit.subreddit(subreddit).new(limit=10):
                if submission.id in cache:
                    continue

                if submission.created_utc <= bot_started_at:
                    continue

                logging.info(f"{submission.title} was posted by /u/{submission.author.name}")

                embed = discord.Embed(
                    title="r/" + subreddit + " - " + submission.title,
                    url=f"https://reddit.com{submission.permalink}",
                    description=submission.selftext[0:350],
                )

                embed.set_author(
                    name=f"/u/{submission.author.name}",
                    url=f"https://reddit.com/u/{submission.author.name}"
                )

                embed.set_thumbnail(url=submission.author.icon_img)

                if len(submission.selftext) > 350:
                    embed.description = embed.description + "..."

                channel = bot.get_channel(config.REDDIT_POSTS_CHANNEL_ID)
                if not channel:
                    logging.info(f"Unable to find channel to post: {submission.title} by /u/{submission.author.name}")
                    continue

                await channel.send(embed=embed)
                cache.append(submission.id)

            await asyncio.sleep(3)

        except Exception as e:
            logging.error(e)
            traceback.print_exc()
            time.sleep(30)
            pass
