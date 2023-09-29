import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger as log

from chiya.config import config
from chiya.utils import embeds


class ReportCloseButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Report",
        style=discord.ButtonStyle.danger,
        custom_id="close_report",
        emoji="🔒",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """
        The close button to close and archive an existing report.
        """
        role_staff = discord.utils.get(interaction.message.guild.roles, id=config["roles"]["staff"])
        if role_staff not in interaction.user.roles:
            embed = embeds.make_embed(
                title="Failed to close report",
                description="You do not have the permission to close this report.",
                color=discord.Color.red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        close_embed = embeds.make_embed(
            color=discord.Color.blurple(),
            description="The report will be closed shortly...",
        )
        await interaction.response.send_message(embed=close_embed)
        await asyncio.sleep(3)
        await interaction.channel.delete()


class ReportMessageButtons(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.value = None

    @discord.ui.button(
        label="Submit Report",
        style=discord.ButtonStyle.primary,
        custom_id="submit_report",
    )
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """
        Create a View for the report message embed confirmation button.
        """
        embed = embeds.make_embed(description="Your report has been submitted.", color=discord.Color.blurple())
        await interaction.response.edit_message(embed=embed, view=None)
        self.value = True
        self.stop()

    @discord.ui.button(
        label="Cancel Report",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel_report",
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """
        Create a View for the report message embed cancel button.
        """
        embed = embeds.make_embed(description="Your report has been canceled.")
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


class ReportMessageApp(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.report_message_command = app_commands.ContextMenu(name="Report Message", callback=self.report_message)
        self.bot.tree.add_command(self.report_message_command)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """
        Register the close report button that persists between bot
        restarts.
        """
        self.bot.add_view(ReportCloseButton())

    @app_commands.guilds(config["guild_id"])
    @app_commands.guild_only()
    async def report_message(self, ctx: discord.Interaction, message: discord.Message) -> None:
        """
        Context menu command for reporting messages to staff.
        """
        await ctx.response.defer(thinking=True, ephemeral=True)

        if ctx.channel.category_id in [
            config["categories"]["moderation"],
            config["categories"]["development"],
            config["categories"]["logs"],
            config["categories"]["tickets"],
        ]:
            return await embeds.error_message(
                ctx=ctx,
                description="You do not have permissions to use this command in this category.",
            )

        if message.author.bot:
            return await embeds.error_message(
                ctx=ctx,
                description="You do not have permissions to use this command on this user.",
            )

        category = discord.utils.get(ctx.guild.categories, id=config["categories"]["tickets"])
        report = discord.utils.get(category.text_channels, name=f"report-{message.id + ctx.user.id}")
        if report:
            return await embeds.error_message(ctx, description=f"You already have a report open: {report.mention}")

        embed = embeds.make_embed(
            title="Reporting message",
            description=(
                f"You are about to report {message.author.mention}'s message. "
                "Are you sure you want to report this message? "
                "Reporting this message will open a new report ticket and staff will be alerted to your report."
            ),
            fields=[
                {"name": "Author:", "value": message.author.mention, "inline": True},
                {"name": "Channel:", "value": message.channel.mention, "inline": True},
                {"name": "Link:", "value": message.jump_url, "inline": False},
            ],
            footer="Abusing reports will result in a ban. Only use this feature for serious reports.",
            color=discord.Color.blurple(),
        )

        if message.clean_content:
            embed.add_field(
                name="Message:",
                value=f">>> {message.clean_content[0:1023]}",
                inline=False,
            )
        for attachment in message.attachments:
            embed.add_field(name="Attachment:", value=attachment.url, inline=False)

        view = ReportMessageButtons()
        await ctx.followup.send(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            channel = await ctx.guild.create_text_channel(
                name=f"report-{message.id + ctx.user.id}",
                category=category,
                overwrites={
                    discord.utils.get(ctx.guild.roles, id=config["roles"]["staff"]): discord.PermissionOverwrite(
                        read_messages=True
                    ),
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.user: discord.PermissionOverwrite(read_messages=True),
                },
            )

            embed = embeds.make_embed(
                title="Reported message",
                description=(
                    "Staff have been alerted about your report. "
                    "Your report will be reviewed at their earliest convenience. "
                    "If you have any supporting details you would like to add to your report, you may do so now."
                ),
                footer="Reported message originally sent",
                timestamp=message.created_at,
                fields=[
                    {
                        "name": "Author:",
                        "value": message.author.mention,
                        "inline": True,
                    },
                    {
                        "name": "Channel:",
                        "value": message.channel.mention,
                        "inline": True,
                    },
                    {
                        "name": "Reported By:",
                        "value": ctx.user.mention,
                        "inline": True,
                    },
                    {"name": "Link:", "value": message.jump_url, "inline": False},
                ],
            )

            if message.clean_content:
                embed.add_field(
                    name="Message:",
                    value=f">>> {message.clean_content[0:1023]}",
                    inline=False,
                )

            for attachment in message.attachments:
                embed.add_field(name="Attachment:", value=attachment.url, inline=False)

            await channel.send(embed=embed, view=ReportCloseButton())

            await channel.send(ctx.user.mention, delete_after=1)
            await channel.send("@here", delete_after=1)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReportMessageApp(bot))
    log.info("App loaded: report_message")
