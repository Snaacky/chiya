import pytest
import asyncio
import discord
import discord.ext.test as dpytest
import discord.ext.commands as commands

@pytest.fixture
def bot(event_loop):
    bot = commands.Bot(
        command_prefix="!", # For some reason, config isn't accessible from this file...?
        intents=discord.Intents(messages=True, guilds=True, members=True, bans=True, reactions=True),
        case_insensitive=True,
        loop=event_loop # Needed for dpytest
    )
    dpytest.configure(bot)
    return bot

@pytest.mark.asyncio
async def test_count(bot):
    await dpytest.message("!count")
    assert dpytest.verify().message().isnumeric()


asyncio.run(test_count(bot))