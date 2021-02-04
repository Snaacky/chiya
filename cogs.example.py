"""
This File is for demonstrating and used as a template for future cogs.
"""

import logging

from discord.ext import commands
from utils import embeds
from utils.record import record_usage


# Enabling logs
log = logging.getLogger(__name__)


class SimpleCog(commands.Cog):
    """SimpleCog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.before_invoke(record_usage)
    @commands.command(name='repeat', aliases=['copy', 'mimic'])
    async def do_repeat(self, ctx, *, our_input: str):
        """A simple command which repeats our input.
        In rewrite Context is automatically passed to our commands as the first argument after self."""

        await ctx.send(our_input)

    # This is an example of a guild only command
    @commands.before_invoke(record_usage)
    @commands.command(name='add', aliases=['plus'])
    @commands.guild_only()
    async def do_addition(self, ctx, first: int, second: int):
        """A simple command which does addition on two integer values."""

        total = first + second
        await ctx.send(f'The sum of **{first}** and **{second}**  is  **{total}**')

    # This is an example of a Owner only command
    @commands.before_invoke(record_usage)
    @commands.command(name='me')
    @commands.is_owner()
    async def only_me(self, ctx):
        """A simple command which only responds to the owner of the bot."""

        await ctx.send(f'Hello {ctx.author.mention}. This command can only be used by you!!')

    # This is an example of a embed command
    @commands.before_invoke(record_usage)
    @commands.command(name='embeds')
    async def example_embed(self, ctx):
        """A simple command which showcases the use of embeds.

        Have a play around and visit the Visualizer."""

        embed = embeds.make_embed(ctx, title='Example Embed', description='Showcasing the use of Embeds...\n'
                                                                    'See the visualizer for more info.', )
        embed.set_author(name='MysterialPy', url='https://gist.github.com/MysterialPy/public',
                         icon_url='http://i.imgur.com/ko5A30P.png')
        embed.set_image(url='https://cdn.discordapp.com/attachments/84319995256905728/252292324967710721/embed.png')

        embed.add_field(name='Embed Visualizer', value='[Click Here!](https://leovoel.github.io/embed-visualizer/)')
        embed.add_field(name='Command Invoker', value=ctx.author.mention)
        embed.set_footer(text='Made in Python with discord.py@rewrite', icon_url='http://i.imgur.com/5BFecvA.png')

        await ctx.send(content='**A simple Embed for discord.py@rewrite in cogs.**', embed=embed)

    # Here is an example of a listener
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Event Listener which is called when a user is banned from the guild.
        For this example I will keep things simple and just print some info.
        Notice how because we are in a cog class we do not need to use @bot.event

        For more information:
        http://discordpy.readthedocs.io/en/rewrite/api.html#discord.on_member_ban

        Check above for a list of events.
        """

        print(f'{user.name}-{user.id} was banned from {guild.name}-{guild.id}')

    # Here is an example of nested commands
    @commands.before_invoke(record_usage)
    @commands.group()
    async def what(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid group command passed...')

    @what.command(name="when")
    async def when(self, ctx):  # Output: <User> used when at <Time>
        await ctx.send('and i have existed since {}'.format(ctx.bot.user.created_at))

    @what.command(name="where")
    async def where(self, ctx):  # Output: <Nothing>
        await ctx.send('on Discord')


# The setup function below is necessary. Remember we give bot.add_cog() the name of the class in this case SimpleCog.
# When we load the cog, we use the name of the file.
def setup(bot) -> None:
    """Load the SimpleCog cog."""
    bot.add_cog(SimpleCog(bot))
    log.info("Cog loaded: SimpleCog")
