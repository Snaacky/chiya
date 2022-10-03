import logging
import time

import asyncpraw
import discord
from discord.ext import commands, tasks

from chiya import config


log = logging.getLogger(__name__)


class RedditTasks(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot_started_at = time.time()
        self.cache = []
        self.client_id = config.get("reddit", {}).get("client_id")
        self.client_secret = config.get("reddit", {}).get("client_secret")
        self.user_agent = config.get("reddit", {}).get("user_agent")
        self.subreddit = config.get("reddit", {}).get("subreddit")
        self.channel = config.get("reddit", {}).get("channel")

        if not all([self.client_id, self.client_secret, self.user_agent, self.subreddit, self.channel]):
            log.warning("Reddit functionality is disabled due to missing prerequisites")
            return

        self.reddit = asyncpraw.Reddit(
            client_id=self.client_id, client_secret=self.client_secret, user_agent=self.user_agent
        )

        log.info("Starting reddit functionality background task")
        self.check_for_posts.start()

    def cog_unload(self) -> None:
        self.check_for_posts.cancel()

    @tasks.loop(seconds=5)
    async def check_for_posts(self) -> None:
        """
        Posts new reddit submissions to channel specified in config
        """
        # Needed to fix bot crashes when reddit is down during startup.
        await self.bot.wait_until_ready()

        try:
            subreddit = await self.reddit.subreddit(config["reddit"]["subreddit"])
            async for submission in subreddit.new(limit=10):
                if submission.id in self.cache or submission.created_utc <= self.bot_started_at:
                    continue

                await submission.author.load()
                await submission.subreddit.load()

                embed = discord.Embed(
                    title=submission.title[0:252],
                    url=f"https://reddit.com{submission.permalink}",
                    description=submission.selftext[0:350],  # Cuts off the description.
                )

                embed.set_author(
                    name=submission.author.name,
                    url=f"https://reddit.com/u/{submission.author.name}",
                    icon_url=submission.author.icon_img,
                )

                embed.set_footer(
                    text=f"{submission.link_flair_text} posted on /r/{submission.subreddit}",
                    icon_url=submission.subreddit.community_icon,
                )

                # Adds ellipsis if the data is too long to signify cutoff.
                if len(submission.title) >= 252:
                    embed.title = embed.title + "..."

                if len(submission.selftext) >= 350:
                    embed.description = embed.description + "..."

                if not isinstance(self.channel, discord.TextChannel):
                    self.channel = await self.bot.fetch_channel(self.channel)

                log.info(f"{submission.title} was posted by /u/{submission.author.name}")
                await self.channel.send(embed=embed)
                self.cache.append(submission.id)

        # Catch all to avoid crashing when reddit has issues.
        except Exception as e:
            log.error(e)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RedditTasks(bot))
    log.info("Tasks loaded: reddit")
