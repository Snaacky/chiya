import time
import logging

import asyncpraw
import asyncio
from asyncpraw.reddit import Submission
import discord
from discord.ext import tasks, commands

import config

log = logging.getLogger(__name__)

reddit = asyncpraw.Reddit(
    client_id=config.client_id,
    client_secret=config.client_secret,
    user_agent=config.user_agent,
    username = config.reddit_username,
    password = config.reddit_password
)

class RedditTask(commands.Cog):
    """Reddit Background Task"""
    def __init__(self, bot):
        self.bot = bot
        if config.subreddit and config.reddit_posts:
            # Only start if there is a place to post and a subreddit to monitor.
            log.info("Starting loop for polling reddit")
            self.check_for_posts.start()
            self.cache = []
            self.bot_started_at = time.time()
            self.check_modqueue.start()
            self.modqueue_cache = []
        else:
            log.warning("Subreddit or discord channel to post is missing from config.")

    def cog_unload(self):
        self.check_for_posts.cancel()

    # Loop 3 seconds to avoid ravaging the CPU and Reddit's API.
    @tasks.loop(seconds=config.poll_rate)
    async def check_for_posts(self):
        """Checking for new reddit posts"""
        # Wait before starting or else new posts may not post to discord.
        await self.bot.wait_until_ready()

        try:
            subreddit = await reddit.subreddit(config.subreddit)
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
                channel = self.bot.get_channel(config.reddit_posts)
                if not channel:
                    log.warning(f"Unable to find channel to post: {submission.title} by /u/{submission.author.name}")
                    continue

                # Sends embed into the Discord channel and adds to cache to avoid dupes in the future.
                await channel.send(embed=embed)
                self.cache.append(submission.id)

        # Catch all exceptions to avoid crashing and log the error.
        except Exception as e:
            log.error(e)

    # Loop 3 seconds to avoid ravaging the CPU and Reddit's API.
    @tasks.loop(seconds=config.poll_rate)
    async def check_modqueue(self):
        """Checking for new modqueue items."""
        # Wait before starting or else new posts may not post to discord.
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

        try:
            subreddit = await reddit.subreddit(config.subreddit)
            
            async for modqueue_item in subreddit.mod.modqueue(limit=None):
                # Skips over any posts already stored in cache.
                if modqueue_item.id in self.modqueue_cache:
                    continue

                # Skips over any posts from before the bot started to avoid infinite loops.
                if modqueue_item.created_utc <= self.bot_started_at:
                    continue

                # Loads the subreddit and author so we can access extra data.
                await modqueue_item.load()

                reason = ""
                async for log in subreddit.mod.log(mod='AutoModerator',limit=5):
                    if modqueue_item.fullname == log.target_fullname:
                        reason = log.details

                await modqueue_item.author.load()
                await modqueue_item.subreddit.load()
                
                if type(modqueue_item) is Submission:
                    embed = discord.Embed(
                        title=modqueue_item.title[0:252],
                        url=f"https://reddit.com{modqueue_item.permalink}",
                        description=modqueue_item.selftext[0:350],  # Cuts off the description.
                    )
                    embed.set_author(
                    name=modqueue_item.author.name,
                    url=f"https://reddit.com/u/{modqueue_item.author.name}",
                    )

                    embed.set_footer(
                        text=f"Removal reason: {reason}",
                        icon_url=modqueue_item.subreddit.community_icon)

                    # Adds ellipsis if the data is too long to signify cutoff.
                    if len(modqueue_item.selftext) >= 350:
                        embed.description = embed.description + "..."

                    if len(modqueue_item.title) >= 252:
                        embed.title = embed.title + "..."
                else:
                    # The submission has to be a comment, mentioning that in title.
                    embed = discord.Embed(title="Comment removed", 
                        description=modqueue_item.body[0:350],
                        url=f"https://reddit.com{modqueue_item.permalink}" 
                    )

                    # Adds ellipsis if the data is too long to signify cutoff.
                    if len(modqueue_item.body) >= 350:
                        embed.description = embed.description + "..."
                    
                    # Setting the embed author to the comment author.
                    embed.set_author(
                    name=modqueue_item.author.name,
                    url=f"https://reddit.com/u/{modqueue_item.author.name}",
                    icon_url=modqueue_item.author.icon_img
                    )
                    
                    embed.set_footer(
                        text=f"Removal reason: {reason}",
                        icon_url=modqueue_item.subreddit.community_icon)

                # Attempts to find the channel to send to and skips if unable to locate.
                channel = self.bot.get_channel(config.modqueue)
                if not channel:
                    continue

                # Sends embed into the Discord channel and adds to cache to avoid dupes in the future.
                await channel.send(embed=embed)
                self.modqueue_cache.append(modqueue_item.id)

        # Catch all exceptions to avoid crashing and log the error.
        except Exception as e:
            log.error(e)

def setup(bot) -> None:
    """ Load the RedditTask cog. """
    bot.add_cog(RedditTask(bot))
    log.info("Task loaded: reddit")
