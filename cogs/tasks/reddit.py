import logging
import os
import time

import asyncpraw
import discord
from discord.ext import tasks, commands

from cogs.commands import settings

log = logging.getLogger(__name__)

class RedditTask(commands.Cog):
    """ Reddit Background Task """

    def __init__(self, bot):
        self.bot = bot

        # Attempt to get the environment variables, defaults to None if non-existent.
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = os.getenv("REDDIT_USER_AGENT")

        # Only define the object if all the env variable prerequisites exist.
        if not all([self.client_id, self.client_secret, self.user_agent]):
            log.warning("Reddit functionality is disabled due to missing prerequisites")
            return

        # Only start the task if the needed prerequisites exist in the settings database.
        if not all([settings.get_value("subreddit"), settings.get_value("channel_reddit"), settings.get_value("poll_rate")]):
            log.warning("Reddit functionality is disabled due to missing prerequisites")
            return

        self.reddit = asyncpraw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent
        )

        log.info("Starting reddit functionality background task")
        self.cache = []
        self.bot_started_at = time.time()
        self.check_for_posts.start() 

    def cog_unload(self):
        self.check_for_posts.cancel()

    @tasks.loop(seconds=settings.get_value("poll_rate"))
    async def check_for_posts(self):
        """ Checking for new reddit posts """
        # Wait before starting or else new posts may not post to discord.
        await self.bot.wait_until_ready()

        try:
            subreddit = await self.reddit.subreddit(settings.get_value("subreddit"))
            # Grabs 10 latest posts, we should never get more than 10 new submissions in < 10 seconds.
            async for submission in subreddit.new(limit=10):
                # Skips over any posts already stored in cache.
                if submission.id in self.cache:
                    continue

                # Skips over any posts from before the bot started to avoid infinite loops.
                if submission.created_utc <= self.bot_started_at:
                    continue

                # Loads the subreddit and author so we can access extra data.
                await submission.author.load()
                await submission.subreddit.load()

                log.info(f"{submission.title} was posted by /u/{submission.author.name}")

                # Builds and populates the embed.
                embed = discord.Embed(
                    title=submission.title[0:252],
                    url=f"https://reddit.com{submission.permalink}",
                    description=submission.selftext[0:350],  # Cuts off the description.
                )

                embed.set_author(
                    name=submission.author.name,
                    url=f"https://reddit.com/u/{submission.author.name}",
                    icon_url=submission.author.icon_img
                )

                embed.set_footer(
                    text=f"{submission.link_flair_text} posted on /r/{submission.subreddit}",
                    icon_url=submission.subreddit.community_icon)

                # Adds ellipsis if the data is too long to signify cutoff.
                if len(submission.selftext) >= 350:
                    embed.description = embed.description + "..."

                if len(submission.title) >= 252:
                    embed.title = embed.title + "..."

                # Attempts to find the channel to send to and skips if unable to locate.
                channel = self.bot.get_channel(settings.get_value("channel_reddit"))
                if not channel:
                    log.warning(f"Unable to find channel to post: {submission.title} by /u/{submission.author.name}")
                    continue

                # Sends embed into the Discord channel and adds to cache to avoid dupes in the future.
                await channel.send(embed=embed)
                self.cache.append(submission.id)

        # Catch all exceptions to avoid crashing and log the error.
        except Exception as e:
            log.error(e)


def setup(bot) -> None:
    """ Load the reddit cog. """
    bot.add_cog(RedditTask(bot))
    log.info("Task loaded: reddit")
