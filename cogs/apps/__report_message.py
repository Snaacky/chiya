import logging

import discord
from discord.ext.commands import Cog, Bot
from discord_slash import cog_ext
from discord_slash.context import MenuContext
from discord_slash.model import ContextMenuType, ButtonStyle
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component

from utils.config import config
from utils import embeds


log = logging.getLogger(__name__)


class ReportMessageCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_context_menu(
        target=ContextMenuType.MESSAGE,
        name="Report message",
        guild_ids=[config["guild_id"]]
    )
    async def report_message(self, ctx: MenuContext):
        """
        Context menu command for reporting messages to staff.

        Args:
            ctx (MenuContext): The context of the context menu.

        TODO:
            Fix "Deferred response might not be what you set it to!" warning.
            Add archive to the category ID check
            Rename "tickets" to something more fitting.
            Make alert embed usage consistent rather than handcrafting some embeds.
        """
        await ctx.defer(hidden=True)

        if ctx.channel.category_id in [
                config["categories"]["moderation"],
                config["categories"]["development"],
                config["categories"]["logs"],
                config["categories"]["tickets"]]:
            return await embeds.error_message(
                ctx=ctx,
                description="You do not have permissions to use this command in this category."
            )

        if ctx.target_message.author.bot:
            return await embeds.error_message(
                ctx=ctx,
                description="You do not have permissions to use this command on this user."
            )

        category = discord.utils.get(ctx.guild.categories, id=config["categories"]["tickets"])
        report = discord.utils.get(category.text_channels, name=f"report-{ctx.target_message.id + ctx.author.id}")
        if report:
            return await embeds.error_message(ctx, description=f"You already have a report open: {report.mention}")

        buttons = [
            create_button(
                style=ButtonStyle.primary,
                label="Submit report",
                custom_id="submit_report"
            ),
            create_button(
                style=ButtonStyle.secondary,
                label="Cancel report",
                custom_id="cancel_report"
            ),
        ]
        action_row = [create_actionrow(*buttons)]

        embed = embeds.make_embed(
            title="Reporting message",
            description=(
                f"You are about to report {ctx.target_message.author.mention}'s message. "
                "Are you sure you want to report this message? "
                "Reporting this message will open a new report ticket and staff will be alerted to your report."
            )
        )
        embed.add_field(name="Author:", value=ctx.target_message.author.mention, inline=True)
        embed.add_field(name="Channel:", value=ctx.target_message.channel.mention, inline=True)
        if ctx.target_message.clean_content:
            embed.add_field(name="Message:", value=f">>> {ctx.target_message.clean_content[0:1023]}", inline=False)
        for attachment in ctx.target_message.attachments:
            embed.add_field(name="Attachment:", value=attachment.url, inline=False)
        embed.add_field(name="Link:", value=ctx.target_message.jump_url, inline=False)
        embed.set_footer(text="Abusing reports will result in a ban. Only use this feature for serious reports.")
        await ctx.send(embed=embed, components=action_row, hidden=True)

        button_ctx = await wait_for_component(self.bot, components=action_row)
        match button_ctx.custom_id:
            case "cancel_report":
                embed = embeds.make_embed(description="Your report has been canceled.")
            case "submit_report":
                channel = await ctx.guild.create_text_channel(
                    name=f"report-{ctx.target_message.id + ctx.author.id}",
                    category=category,
                    overwrites={
                        discord.utils.get(ctx.guild.roles, id=config["roles"]["trial_mod"]): discord.PermissionOverwrite(read_messages=True),
                        discord.utils.get(ctx.guild.roles, id=config["roles"]["staff"]): discord.PermissionOverwrite(read_messages=True),
                        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        ctx.author: discord.PermissionOverwrite(read_messages=True),
                    },
                )

                embed = embeds.make_embed(title="Reported message")
                embed.add_field(name="Author:", value=ctx.target_message.author.mention, inline=True)
                embed.add_field(name="Channel:", value=ctx.target_message.channel.mention, inline=True)
                embed.add_field(name="Reported By:", value=ctx.author.mention, inline=True)
                if ctx.target_message.clean_content:
                    embed.add_field(name="Message:", value=f">>> {ctx.target_message.clean_content[0:1023]}", inline=False)
                for attachment in ctx.target_message.attachments:
                    embed.add_field(name="Attachment:", value=attachment.url, inline=False)
                embed.add_field(name="Link:", value=ctx.target_message.jump_url, inline=False)
                embed.set_footer(text="Reported message originally sent")
                embed.timestamp = ctx.target_message.created_at
                await channel.send(embed=embed)

                embed = embeds.make_embed(description=(
                    "Staff have been alerted about your report. "
                    "Your report will be reviewed at their earliest convenience. "
                    "If you have any supporting details you would like to add to your report, you may do so now."
                ))
                await channel.send(embed=embed)

                await channel.send(ctx.author.mention, delete_after=1)
                await channel.send("@here", delete_after=1)

                embed = embeds.make_embed(
                    description=f"Your report has been successfully created: {channel.mention}",
                    color="soft_green"
                )
        await button_ctx.edit_origin(embed=embed, components=None, hidden=True)


def setup(bot: Bot) -> None:
    bot.add_cog(ReportMessageCog(bot))
    log.info("App loaded: report_message")
