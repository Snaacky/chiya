import asyncio
import logging
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord.message import Message
from discord_slash import cog_ext, SlashContext
from discord_slash.context import ComponentContext
from discord_slash.model import ButtonStyle, SlashCommandPermissionType
from discord_slash.utils.manage_commands import (
    create_option,
    create_permission
)
from discord_slash.utils.manage_components import (
    create_actionrow,
    create_button,
    wait_for_component,
)

from cogs.commands import settings
from utils import embeds
from utils.record import record_usage

# Enabling logs
log = logging.getLogger(__name__)


class EmbedGeneratorCog(Cog):
    """EmbedGeneratorCog Cog"""

    def __init__(self, bot):
        self.bot = bot
    
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.before_invoke(record_usage)
    @cog_ext.cog_slash(
        name="create_embed",
        description="Creates an embed from the specified parameters.",
        guild_ids=[settings.get_value("guild_id")],
        options=[
            create_option(
                name="title", description="Embed title.", option_type=3, required=False
            ),
            create_option(
                name="description",
                description="Embed description.",
                option_type=3,
                required=False,
            ),
            create_option(
                name="url", description="Embed URL", option_type=3, required=False
            ),
            create_option(
                name="footer",
                description="Embed footer.",
                option_type=3,
                required=False,
            ),
            create_option(
                name="footer_icon_url",
                description="Embed footer icon URL.",
                option_type=3,
                required=False,
            ),
            create_option(
                name="color", description="Embed color.", option_type=3, required=False
            ),
            create_option(
                name="use_author",
                description="Whether to use the command invocation author as embed author.",
                option_type=5,
                required=False,
            ),
            create_option(
                name="thumbnail_url",
                description="URL for the thumbnail parameter of the embed.",
                option_type=3,
                required=False,
            ),
            create_option(
                name="image_url",
                description="URL for the image parameter of the embed.",
                option_type=3,
                required=False,
            ),
        ],
        default_permission=False,
        permissions={
            settings.get_value("guild_id"): [
                create_permission(
                    settings.get_value("role_staff"),
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
                create_permission(
                    settings.get_value("role_trial_mod"),
                    SlashCommandPermissionType.ROLE,
                    True,
                ),
            ]
        },
    )
    async def embed_generator(
        self,
        ctx: SlashContext,
        title: str = "",
        description: str = "",
        url: str = "",
        footer: str = "",
        footer_icon_url: str = "",
        color: str = "default",
        use_author: bool = True,
        thumbnail_url: str = None,
        image_url: str = None,
    ):
        await ctx.defer()

        embed = embeds.make_embed(
            ctx=ctx,
            title=title,
            description=description,
            color=color,
            thumbnail_url=thumbnail_url,
            image_url=image_url,
            author=use_author,
        )

        if not use_author:
            embed.timestamp = discord.Embed.Empty

        if footer:
            embed.set_footer(text=footer, icon_url=footer_icon_url)

        embed.url = url

        if len(embed) > 6000:
            await embeds.error_message(ctx=ctx, description="The embed is too big!")

        embed_message: Message = await ctx.send(embed=embed)
        buttons_main_menu = [
            create_button(
                style=ButtonStyle.green, label="Save", custom_id="save_button"
            ),
            create_button(
                style=ButtonStyle.red, label="Delete", custom_id="delete_button"
            ),
            create_button(
                style=ButtonStyle.blurple, label="Edit", custom_id="edit_button"
            ),
            create_button(
                style=ButtonStyle.blurple, label="Add Field", custom_id="add_field_button"
            ),
        ]
        buttons_edit_menu = [
            create_button(
                style = ButtonStyle.blurple, label = "Edit title", custom_id="edit_title_button"
            ),
            create_button(
                style = ButtonStyle.blurple, label = "Edit description", custom_id = "edit_description_button"
            ),
            create_button(
                style = ButtonStyle.blurple, label = "Edit field", custom_id = "edit_field_button"
            ),
            create_button(
                style = ButtonStyle.blurple, label = "Back to main menu", custom_id = "main_menu_button"
            ),
            
        ]
        buttons_edit_field_menu = [
            create_button(
                style = ButtonStyle.blurple, label = "Edit name", custom_id="edit_field_name_button"
            ),
            create_button(
                style = ButtonStyle.blurple, label = "Edit value", custom_id = "edit_field_value_button"
            ),
            create_button(
                style = ButtonStyle.blurple, label = "Toggle inline", custom_id = "toggle_inline_button"
            ),
            create_button(
                style = ButtonStyle.red, label = "Remove Field", custom_id = "remove_field_button"
            ),

        ]
        action_row_main_menu = create_actionrow(*buttons_main_menu)
        action_row_edit_menu = create_actionrow(*buttons_edit_menu)
        action_row_edit_field_menu = create_actionrow(*buttons_edit_field_menu)
        await embed_message.edit(components=[action_row_main_menu])
        
        def check_message(message):
            return message.author == ctx.author
        
        def edit_embed_field (embed: discord.Embed, field: str, new_value: str) -> discord.Embed:
            embed = embed.to_dict()
            embed[field] = new_value
            return discord.Embed.from_dict(embed)
        
        def mark_embed_fields(embed: discord.Embed) -> discord.Embed:
            embed = embed.to_dict()
            for i,field in enumerate(embed['fields']):
                embed['fields'][i]['name'] = f"{i}: {field['name']}"
            return discord.Embed.from_dict(embed)
        
        def edit_field_at(embed: discord.Embed, field_index: int, field_name: str, updated_value: str) -> discord.Embed:
            embed = embed.to_dict()
            embed['fields'][field_index][field_name] = updated_value
            return discord.Embed.from_dict(embed)
        
        def remove_field_at(embed: discord.Embed, field_index: int) -> discord.Embed:
            embed = embed.to_dict()
            embed_fields = embed['fields']
            embed_fields.pop(field_index)
            embed['fields'] = embed_fields
            return discord.Embed.from_dict(embed)

        while True:
            try:
                button_ctx: ComponentContext = await wait_for_component(
                    self.bot, components=[action_row_main_menu], messages=embed_message, timeout=30
                )
                await button_ctx.defer(edit_origin=True)
                
                match button_ctx.custom_id:
                    case "save_button":
                        await embed_message.edit(components=[])
                        return

                    case "edit_button":
                        while True:
                            await embed_message.edit(components=[action_row_edit_menu])
                            button_ctx: ComponentContext = await wait_for_component(
                                self.bot, components=[action_row_edit_menu], messages=embed_message, timeout=30
                            )
                            await button_ctx.defer(edit_origin=True)
                            match button_ctx.custom_id:
                                case "edit_title_button":
                                    await embed_message.edit(content="Enter new title:")
                                    message = await ctx.bot.wait_for("message", timeout=30, check=check_message)
                                    await message.delete()
                                    embed = edit_embed_field(embed, "title", message.content)
                                    await embed_message.edit(content="", embed=embed)
                                
                                case "edit_description_button":
                                    await embed_message.edit(content="Enter new description:")
                                    message = await ctx.bot.wait_for("message", timeout=30, check=check_message)
                                    await message.delete()
                                    embed = edit_embed_field(embed, "description", message.content)
                                    await embed_message.edit(content="", embed=embed)
                            
                                case "edit_field_button":
                                    if "fields" in embed.to_dict().keys():
                                        await embed_message.edit(embed=mark_embed_fields(embed), content="Enter the field ID to edit:", components=[])
                                        message = await ctx.bot.wait_for("message", timeout=30, check=check_message)
                                        await message.delete()
                                        field_index = int(message.content)
                                        if field_index < len(embed.to_dict()['fields']) and field_index >= 0:
                                            await embed_message.edit(embed=embed, components=[action_row_edit_field_menu])
                                            button_ctx: ComponentContext = await wait_for_component(
                                                self.bot, components=[action_row_edit_field_menu], messages=embed_message,   timeout=30
                                            )
                                            await button_ctx.defer(edit_origin=True)
                                            match button_ctx.custom_id:
                                                case "edit_field_name_button":
                                                    await embed_message.edit(content="Enter new field name:", components=[])
                                                    message = await ctx.bot.wait_for("message", timeout=30, check=check_message)
                                                    await message.delete()
                                                    new_field_name = message.content
                                                    embed = edit_field_at(embed, field_index, "name", new_field_name)
                                                    await embed_message.edit(embed=embed, content="")
                                                    
                                                case "edit_field_value_button":
                                                    await embed_message.edit(content="Enter new field value:", components=[])
                                                    message = await ctx.bot.wait_for("message", timeout=30, check=check_message)
                                                    await message.delete()
                                                    new_field_value = message.content
                                                    embed = edit_field_at(embed, field_index, "value", new_field_value)
                                                    await embed_message.edit(embed=embed, content="")

                                                case "toggle_inline_button":
                                                    new_inline_state = not embed.to_dict()['fields'][field_index]['inline']
                                                    embed = edit_field_at(embed, field_index, "inline", new_inline_state)
                                                    await embed_message.edit(embed=embed)
                                                    
                                                case "remove_field_button":
                                                    embed = remove_field_at(embed, field_index)
                                                    await embed_message.edit(embed=embed) 
                                
                                case "main_menu_button":
                                    break
                    
                    case "add_field_button":
                        await embed_message.edit(content="Enter name of field:")
                        message = await ctx.bot.wait_for("message", timeout=30, check=check_message)
                        await message.delete()
                        field_name = message.content
                        await embed_message.edit(content="Enter value of field:")
                        message = await ctx.bot.wait_for("message", timeout=30, check=check_message)
                        await message.delete()
                        field_value = message.content
                        await embed_message.edit(content="Inline? (y/n)?:")
                        message = await ctx.bot.wait_for("message", timeout=30, check=check_message)
                        await message.delete()
                        field_inline = True if message.content.lower().startswith('y') else False
                        embed.add_field(name=field_name, value=field_value, inline=field_inline)
                        await embed_message.edit(content="", embed=embed)

   
                await embed_message.edit(components=[action_row_main_menu])

            except asyncio.TimeoutError:
                await embed_message.edit(content="", embed=embed, components=[])


def setup(bot: Bot) -> None:
    """Load the AdministrationCog cog."""
    bot.add_cog(EmbedGeneratorCog(bot))
    log.info("Commands loaded: embedgenerator")
