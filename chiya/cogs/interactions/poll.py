import discord
from discord import app_commands
from discord.enums import ButtonStyle
from discord.ext import commands
from discord.interactions import Interaction
from loguru import logger as log

from chiya import database
from chiya.config import config
from chiya.utils import embeds


class PollInteractions(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.eval_command = app_commands.ContextMenu(name="Poll End", callback=self.end)

    class PollGroup(app_commands.Group):
        pass
    poll_group = PollGroup(name="poll", guild_ids=[config["guild_id"]])

    @poll_group.command(name="start", description="Create a poll with specified options.")
    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_server=True)
    @app_commands.describe(amount="The amount of options in the poll.")
    async def start(self, interaction: discord.Interaction, amount: app_commands.Range[int, 2, 9]):
        """
        Opens a modal to create a poll
        """
        await interaction.response.send_modal(PollModal(amount))

    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_server=True)
    async def end(self, interaction: discord.Interaction, message: discord.Message):
        """
        Ends the current selected poll
        """
        await interaction.response.defer()

        if message.author.id != self.bot.user.id:
            return await interaction.followup.send("Message not owned by the bot.")

        if not message.components or message.components[0].custom_id != f"{message.id}_0":
            return await interaction.followup.send("No poll found.")

        votes = ""

        db = database.Database().get()
        statement = 'SELECT option, COUNT(*) AS count FROM poll WHERE message_id = :message_id GROUP BY option'
        for row in db.query(statement, message_id=message.id):
            votes += f"{row['option'] + 1}: {row['count']}"

        view: Poll = Poll.from_message(message)

        embed = embeds.make_embed(
            title="Poll has Ended!",
            description=f"Results Vote on this poll:\n\n{votes}",
            footer="You can vote for multiple options.",
            color=discord.Color.blurple(),
        )
        db.close()
        await message.edit(embed=message.embeds[0], view=view)
        await message.reply(embed=embed)
        await interaction.followup.send("Poll ended", ephemeral=True)


class PollModal(discord.ui.Modal, title="Poll"):

    poll_title = discord.ui.TextInput(
        label='Poll Title',
        placeholder='Title',
    )

    def __init__(self, options: int):
        super().__init__()
        self.options = options
        self.option_elements: list[discord.ui.TextInput] = []

        for i in range(options):
            element = discord.ui.TextInput(label=f"Option {i}", placeholder='Info')
            self.add_item(element)
            self.option_elements.append(element)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        option_message = "\n\n".join(
            [
                f"{option.label}: {option.value}" for option in self.option_elements
            ]
        )

        embed = embeds.make_embed(
            title=self.poll_title.value,
            description=f"Vote on this poll:\n\n{option_message}",
            footer="You can vote for multiple options.",
            color=discord.Color.blurple(),
        )

        message = await interaction.channel.send(embed=embed, view=Poll(self.options, interaction.message.id))

        await interaction.followup.send(f"Added poll to current channel {message.jump_url}", ephemeral=True)


class PollButton(discord.ui.Button['Poll']):
    def __init__(self, index: int, message: int):
        super().__init__(
            style=ButtonStyle.secondary,
            label=str(index + 1),
            row=(index) % 3,
            custom_id=f"{message}_{index}"
        )
        self.index = index

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        db = database.Database().get()
        message_id = interaction.message.id
        user_id = interaction.user.id
        result = db["poll"].find_one(message_id=message_id, user_id=user_id)

        if result:
            db["poll"].delete(message_id=message_id, user_id=user_id)
        else:
            db["poll"].insert(
                dict(
                    message_id=interaction.message.id,
                    user_id=interaction.user.id,
                    option=self.index
                )
            )
        db.commit()
        db.close()

        if result:
            await interaction.followup.send(f"Removed vote for option {self.index + 1}.")
        else:
            await interaction.followup.send(f"Added vote for option {self.index + 1}.")


class Poll(discord.ui.View):
    buttons: list[PollButton]

    def __init__(self, options: int, message: int):
        super().__init__()
        self.options = options

        for i in range(options):
            self.add_item(PollButton(i, message))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PollInteractions(bot))
    log.info("Interactions loaded: ticket")
