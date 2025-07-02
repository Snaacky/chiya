import discord
from discord import Interaction, ui
from discord.ext import menus

FIRST_EMOJI = "\u23ee"  # [:track_previous:]
LEFT_EMOJI = "\u2b05"  # [:arrow_left:]
RIGHT_EMOJI = "\u27a1"  # [:arrow_right:]
LAST_EMOJI = "\u23ed"  # [:track_next:]
DELETE_EMOJI = "⛔"  # [:trashcan:]

PAGINATION_EMOJI = (FIRST_EMOJI, LEFT_EMOJI, RIGHT_EMOJI, LAST_EMOJI, DELETE_EMOJI)


class MyMenuPages(ui.View, menus.MenuPages):
    def __init__(self, source) -> None:
        super().__init__(timeout=60)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.user = None
        self.message = None

    async def start(self, ctx: Interaction, *, channel=None, wait=False) -> None:
        # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
        await self._source._prepare_once()
        self.ctx = ctx
        self.user = ctx.user
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if "view" not in value:
            value.update({"view": self})
        return value

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the author that invoke the command to be able to use the interaction"""
        return interaction.user == self.user

    # This is extremely similar to Custom MenuPages(I will not explain these)
    @ui.button(emoji=discord.PartialEmoji(name="left_end", id=1093296373660651633), style=discord.ButtonStyle.primary)
    async def first_page(self, interaction, clicked_button):
        await self.show_page(0, interaction)

    @ui.button(emoji=discord.PartialEmoji(name="left_prev", id=1093296352626229348), style=discord.ButtonStyle.primary)
    async def before_page(self, interaction, clicked_button):
        await self.show_checked_page(self.current_page - 1, interaction)

    @ui.button(emoji=discord.PartialEmoji(name="right_next", id=1093296333156274186), style=discord.ButtonStyle.primary)
    async def next_page(self, interaction, clicked_button):
        await self.show_checked_page(self.current_page + 1, interaction)

    @ui.button(emoji=discord.PartialEmoji(name="right_end", id=1093296509442871448), style=discord.ButtonStyle.primary)
    async def last_page(self, interaction, clicked_button):
        await self.show_page(self._source.get_max_pages() - 1, interaction)

    async def show_page(self, page_number, interaction: Interaction) -> None:
        page = await self._source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        if interaction.response.is_done():
            await interaction.followup.edit_message(interaction.message.id, **kwargs)
        await interaction.response.edit_message(**kwargs)

    async def show_checked_page(self, page_number, interaction: Interaction) -> None:
        max_pages = self._source.get_max_pages()
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(page_number, interaction)
            elif max_pages > page_number >= 0:
                await self.show_page(page_number, interaction)
            else:
                target = 0
                if page_number < 0:
                    target = max_pages - 1
                await self.show_page(target, interaction)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            await interaction.response.send_message("This page would go out of bounds.", ephemeral=True)

    async def send_initial_message(self, ctx: Interaction, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if ctx.response.is_done():
            return await ctx.followup.send(**kwargs, ephemeral=True)
        return await ctx.response.send_message(**kwargs, ephemeral=True)


class MySource(menus.ListPageSource):
    def __init__(self, data, embed: discord.Embed) -> None:
        super().__init__(data, per_page=4)
        self.embed = embed

    async def format_page(self, menu, entries) -> discord.Embed:
        page_info = await self.get_page(menu.current_page)
        desc = "\n".join(page_info)
        self.embed.description = desc
        self.embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return self.embed
