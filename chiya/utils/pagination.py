import discord
import orjson
from discord import Interaction, ui
from discord.ext import menus
from loguru import logger as log


FIRST_EMOJI = "\u23EE"  # [:track_previous:]
LEFT_EMOJI = "\u2B05"  # [:arrow_left:]
RIGHT_EMOJI = "\u27A1"  # [:arrow_right:]
LAST_EMOJI = "\u23ED"  # [:track_next:]
DELETE_EMOJI = "⛔"  # [:trashcan:]

PAGINATION_EMOJI = (FIRST_EMOJI, LEFT_EMOJI, RIGHT_EMOJI, LAST_EMOJI, DELETE_EMOJI)


class MyMenuPages(ui.View, menus.MenuPages):
    def __init__(self, source):
        super().__init__(timeout=60)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.user = None
        self.message = None

    async def start(self, ctx: Interaction, *, channel=None, wait=False):
        # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
        await self._source._prepare_once()
        self.ctx = ctx
        self.user = ctx.user
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if 'view' not in value:
            value.update({'view': self})
        value["ephemeral"] = True
        return value

    async def interaction_check(self, interaction: discord.Interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""
        return interaction.user == self.user

    # This is extremely similar to Custom MenuPages(I will not explain these)
    @ui.button(emoji='⏮', style=discord.ButtonStyle.blurple)
    async def first_page(self, interaction, clicked_button):
        await self.show_page(0, interaction)

    @ui.button(emoji='⏪', style=discord.ButtonStyle.blurple)
    async def before_page(self, interaction, clicked_button):
        await self.show_checked_page(self.current_page - 1, interaction)

    @ui.button(emoji='⏹', style=discord.ButtonStyle.blurple)
    async def stop_page(self, interaction, clicked_button: Interaction):
        self.stop()
        await interaction.response.send_message("Stopped interaction", ephemeral=True)

    @ui.button(emoji='⏩', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction, clicked_button):
        await self.show_checked_page(self.current_page + 1, interaction)

    @ui.button(emoji='⏭', style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction, clicked_button):
        await self.show_page(self._source.get_max_pages() - 1, interaction)

    async def show_page(self, page_number, interaction: Interaction):
        page = await self._source.get_page(page_number)
        self.current_page = page_number
        log.debug(f"Getting new page info {page_number} | {page}")
        kwargs = await self._get_kwargs_from_page(page)
        log.debug(f"New page info {orjson.dumps(kwargs)}")
        if interaction.response.is_done():
            await interaction.followup.edit_message(interaction.message.id, **kwargs)
        await interaction.response.edit_message(**kwargs)

    async def show_checked_page(self, page_number, interaction: Interaction):
        max_pages = self._source.get_max_pages()
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(page_number, interaction)
            elif max_pages > page_number >= 0:
                await self.show_page(page_number, interaction)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            await interaction.response.send_message("This page would go out of bounds.", ephemeral=True)

    async def send_initial_message(self, ctx: Interaction, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if ctx.response.is_done():
            return await ctx.followup.send(**kwargs)
        return await ctx.response.send_message(**kwargs)


class MySource(menus.ListPageSource):
    def __init__(self, data, embed: discord.Embed):
        super().__init__(data, per_page=4)
        self.embed = embed

    async def format_page(self, menu, entries):
        log.debug(f"FORMAT_PAGE: {menu.current_page} | {menu}")
        page_info = await self.get_page(menu.current_page)
        desc = '\n'.join(page_info)
        self.embed.description = desc
        self.embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return self.embed
