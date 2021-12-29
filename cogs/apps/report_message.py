import logging

import discord
from discord import message_command
from discord.commands import context
from discord.ext import commands

from utils import embeds
from utils.config import config

log = logging.getLogger(__name__)


class ReportMessageButtons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Submit Report", style=discord.ButtonStyle.primary, custom_id="submit_report")
    async def submit(self, button: discord.ui.Button, interaction: discord.Interaction):
        """ Create a View for the report message embed confirmation button. """
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel Report", style=discord.ButtonStyle.secondary, custom_id="cancel_report")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        """ Create a View for the report message embed cancel button. """
        embed = embeds.make_embed(description="Your report has been canceled.")
        await interaction.response.edit_message(embed=embed, view=None)


class ReportMessageApp(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @message_command(guild_ids=config["guild_ids"], name="Report Message")
    async def report_message(self, ctx: context.ApplicationContext, message: discord.Message):
        """ Context menu command for reporting messages to staff. """
        await ctx.defer(ephemeral=True)

        if ctx.channel.category_id in [
            config["categories"]["moderation"],
            config["categories"]["development"],
            config["categories"]["logs"],
            config["categories"]["tickets"]]:
            return await embeds.error_message(ctx=ctx, description="You do not have permissions to use this command in this category.")

        if ctx.author.bot:
            return await embeds.error_message(ctx=ctx, description="You do not have permissions to use this command on this user.")

        category = discord.utils.get(ctx.guild.categories, id=config["categories"]["tickets"])
        report = discord.utils.get(category.text_channels, name=f"report-{message.id + ctx.author.id}")
        if report:
            return await embeds.error_message(ctx, description=f"You already have a report open: {report.mention}")

        embed = embeds.make_embed(
            title="Reporting message",
            description=(
                f"You are about to report {message.author.mention}'s message. "
                "Are you sure you want to report this message? "
                "Reporting this message will open a new report ticket and staff will be alerted to your report."
            ),
            footer="Abusing reports will result in a ban. Only use this feature for serious reports.",
            fields=[
                {"name": "Author:", "value": message.author.mention, "inline": True},
                {"name": "Channel:", "value": message.channel.mention, "inline": True},
            ])

        if message.clean_content:
            embed.add_field(name="Message:", value=f">>> {message.clean_content[0:1023]}", inline=False)
        for attachment in message.attachments:
            embed.add_field(name="Attachment:", value=attachment.url, inline=False)

        embed.add_field(name="Link:", value=message.jump_url, inline=False)

        view = ReportMessageButtons()
        await ctx.send_followup(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            channel = await ctx.guild.create_text_channel(
                name=f"report-{message.id + ctx.author.id}",
                category=category,
                overwrites={
                    discord.utils.get(ctx.guild.roles, id=config["roles"]["staff"]): discord.PermissionOverwrite(read_messages=True),
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.author: discord.PermissionOverwrite(read_messages=True),
                })

            embed = embeds.make_embed(
                title="Reported message",
                footer="Reported message originally sent",
                fields=[
                    {"name": "Author:", "value": message.author.mention, "inline": True},
                    {"name": "Channel:", "value": message.channel.mention, "inline": True},
                    {"name": "Reported By:", "value": ctx.author.mention, "inline": True},
                    {"name": "Link:", "value": message.jump_url, "inline": False},
                ])

            if message.clean_content:
                embed.add_field(name="Message:", value=f">>> {message.clean_content[0:1023]}", inline=False)

            for attachment in message.attachments:
                embed.add_field(name="Attachment:", value=attachment.url, inline=False)

            embed.timestamp = message.created_at
            await channel.send(embed=embed)

            embed = embeds.make_embed(
                description=(
                    "Staff have been alerted about your report. "
                    "Your report will be reviewed at their earliest convenience. "
                    "If you have any supporting details you would like to add to your report, you may do so now."
                ))
            await channel.send(embed=embed)
            await channel.send(ctx.author.mention, delete_after=1)
            # await channel.send("@here", delete_after=1)

            embed = embeds.make_embed(
                description=f"Your report has been successfully created: {channel.mention}",
                color=discord.Color.green(),
            )

            await ctx.send_followup(embed=embed, ephemeral=True)


def setup(bot: commands.bot.Bot) -> None:
    bot.add_cog(ReportMessageApp(bot))
    log.info("App loaded: report_message")
