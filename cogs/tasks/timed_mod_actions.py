import logging
from datetime import datetime, timezone

from discord.ext import tasks
from discord.ext.commands import Bot, Cog, Context

from utils import database, embeds
from utils.config import config


log = logging.getLogger(__name__)


class TimedModActionsTask(Cog):

    def __init__(self, bot: Bot):
        self.bot = bot
        self.check_for_pending_mod_actions.start()

    def cog_unload(self):
        self.check_for_pending_mod_actions.cancel()

    @tasks.loop(seconds=3.0)
    async def check_for_pending_mod_actions(self) -> None:
        await self.bot.wait_until_ready()

        db = database.Database().get()

        results = db["timed_mod_actions"].find(
            is_done=False,
            end_time={"lt": datetime.now(tz=timezone.utc).timestamp()}
        )

        for action in results:
            guild = self.bot.get_guild(config["guild_id"])
            channel = guild.get_channel(config["channels"]["moderation"])
            member = guild.get_member(action["user_id"])

            if action["action_type"] == "mute":
                db["timed_mod_actions"].update(dict(id=action["id"], is_done=True), ["id"])

                embed = embeds.make_embed(
                    title=f"Unmuting member: {member}",
                    description=f"{member.mention} was unmuted as their mute time elapsed.",
                    thumbnail_url="https://i.imgur.com/W7DpUHC.png",
                    color="soft_green"
                )

                mutes = self.bot.get_cog("MuteCog")

                if not await mutes.send_unmuted_dm_embed(member=member, reason="Timed mute lapsed."):
                    embed.add_field(
                        name="Notice:",
                        value=(
                            f"Unable to message {member.mention} about this action. "
                            "This can be caused by the user not being in the server, "
                            "having DMs disabled, or having the bot blocked."
                        )
                    )

                await mutes.unmute_member(member=member, reason="Timed mute lapsed.")
                await mutes.archive_mute_channel(user_id=member.id, reason="Mute time elapsed.")
                await channel.send(embed=embed)

            if action["action_type"] == "restrict":
                db["timed_mod_actions"].update(dict(id=action["id"], is_done=True), ["id"])

                embed = embeds.make_embed(
                    title=f"Unrestricting member: {member}",
                    thumbnail_url="https://i.imgur.com/W7DpUHC.png",
                    description=f"{member.mention} was unrestricted as their restrict time elapsed.",
                    color="soft_green"
                )

                restricts = self.bot.get_cog("RestrictCog")
                if not await restricts.send_unrestricted_dm_embed(member=member, reason="Timed restriction lapsed."):
                    embed.add_field(
                        name="Notice:",
                        value=(
                            f"Unable to message {member.mention} about this action. "
                            "This can be caused by the user not being in the server, "
                            "having DMs disabled, or having the bot blocked."
                        )
                    )

                await restricts.unrestrict_member(member=member, reason="Timed restriction lapsed.")
                await channel.send(embed=embed)

        db.commit()
        db.close()


def setup(bot: Bot) -> None:
    bot.add_cog(TimedModActionsTask(bot))
    log.info("Cog loaded: timed_mod_actions_task")
