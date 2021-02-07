import asyncio
import time
import traceback
import logging

import discord
from discord.ext import tasks, commands
import praw

import config

log = logging.getLogger(__name__)

reddit = praw.Reddit(
    client_id=config.REDDIT_API_CLIENT_ID,
    client_secret=config.REDDIT_API_CLIENT_SECRET,
    user_agent=f"Chiya (for /r/{config.SUBREDDIT_NAME})"
)

subreddit = config.SUBREDDIT_NAME


class RedditTask(commands.Cog):
    """Reddit Background Task"""
    def __init__(self, bot):
        self.bot = bot
        self.cache = []
        self.bot_started_at = time.time()
        self.check_for_posts.start()
        self.cache = []
        self.bot_started_at = time.time()

    def cog_unload(self):
        self.check_for_posts.cancel()

    # Loop 3 seconds to avoid ravaging the CPU and Reddit's API.
    @tasks.loop(seconds=3.0)
    async def check_for_posts(self):
        """Checking for new reddit posts"""
        # Wait before starting because if Reddit is down when the bot starts, the bot will never get to on_ready().
        await self.bot.wait_until_ready()

        try:
            # Grabs 10 latest posts, we should never get more than 10 new submissions in < 10 seconds.
            for submission in reddit.subreddit(subreddit).new(limit=10):
                # Skips over any posts already stored in cache.
                if submission.id in self.cache:
                    continue

                # Skips over any posts from before the bot started to avoid infinite loops.
                if submission.created_utc <= self.bot_started_at:
                    continue

                log.info(f"{submission.title} was posted by /u/{submission.author.name}")

                # Builds and stylizes the embed.
                embed = discord.Embed(
                    title="r/" + subreddit + " - " + submission.title[0:253],
                    url=f"https://reddit.com{submission.permalink}",
                    description=submission.selftext[0:350],  # Cuts off the description.
                )
                embed.set_author(
                    name=f"/u/{submission.author.name}",
                    url=f"https://reddit.com/u/{submission.author.name}"
                )
                embed.set_thumbnail(url=submission.author.icon_img)

                # Adds ellipsis if the data is too long to signify cutoff.
                if len(submission.selftext) > 350:
                    embed.description = embed.description + "..."

                if len(submission.title) > 253:
                    embed.title = embed.title + "..."

                # Attempts to find the channel to send to and skips if unable to locate.
                channel = self.bot.get_channel(config.REDDIT_POSTS_CHANNEL_ID)
                if not channel:
                    # TODO: Port print() to logging system.
                    print(f"Unable to find channel to post: {submission.title} by /u/{submission.author.name}")
                    continue

                # Sends embed into the Discord channel and adds to cache to avoid dupes in the future.
                await channel.send(embed=embed)
                self.cache.append(submission.id)

        # Catch all exceptions to avoid crashing and print the traceback for future debugging.
        except Exception as e:
            print(e)
            traceback.print_exc()


def setup(bot) -> None:
    """ Load the GeneralCog cog. """
    bot.add_cog(RedditTask(bot))
    log.info("Cog loaded: RedditTask")
