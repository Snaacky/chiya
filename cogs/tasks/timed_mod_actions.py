import logging
from datetime import datetime, timezone

from discord.ext import tasks
from discord.ext.commands import Bot, Cog

from utils import database, embeds
from utils.config import config


log = logging.getLogger(__name__)


class TimedModActionsTask(Cog):
    """ Timed Mod Actions Background  """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.check_for_pending_mod_actions.start()

    def cog_unload(self):
        self.check_for_pending_mod_actions.cancel()

    @tasks.loop(seconds=3.0)
    async def check_for_pending_mod_actions(self) -> None:
        """ Checks for mod actions periodically, and reverses them accordingly if the time lapsed. """
        # Wait for bot to start.
        await self.bot.wait_until_ready()

        # Open a connection to the database.
        db = database.Database().get()

        # Query the database for all temporary mod actions that haven't executed yet.
        results = db["timed_mod_actions"].find(
            is_done=False,
            end_time={"lt": datetime.now(tz=timezone.utc).timestamp()}
        )

        for action in results:
            # Get the guild and mod channel to send the expiration notice into.
            guild = self.bot.get_guild(config["guild_ids"][0])
            channel = guild.get_channel(config["channels"]["moderation"])

            if action["action_type"] == "mute":
                # Update the database to mark the mod action as resolved.
                db["timed_mod_actions"].update(dict(id=action["id"], is_done=True), ["id"])

                # Get the MuteCog so that we can access functions from it.
                mutes = self.bot.get_cog("MuteCog")

                # Attempt to get the member if they still exist in the guild.
                member = guild.get_member(action["user_id"])

                # If the user has left the guild, send a message in #moderation and end the function.
                if not member:
                    # Fetch the user object instead because the user is no longer a member of the server.
                    user = await self.bot.fetch_user(action["user_id"])

                    # Creating the embed that will be used to alert the moderator that the user was successfully muted.
                    embed = embeds.make_embed(
                        title=f"Unmuting member: {user}",
                        thumbnail_url="https://i.imgur.com/W7DpUHC.png",
                        color="soft_orange"
                    )
                    embed.description = f"Unmuted {user.mention} because their mute time elapsed but they have since left the server."

                    # Archives the mute channel, sends the embed in the moderation channel, and ends the function.
                    await mutes.archive_mute_channel(user_id=user.id, guild=guild, reason="Mute time elapsed.")
                    return await channel.send(embed=embed)

                # Create the embed that will be used to alert the moderator that the user was successfully muted.
                embed = embeds.make_embed(
                    title=f"Unmuting member: {member}",
                    thumbnail_url="https://i.imgur.com/W7DpUHC.png",
                    color="soft_green"
                )
                embed.description = f"{member.mention} was unmuted as their mute time elapsed."

                # Attempt to DM the user to let them know they were unmuted.
                if not await mutes.send_unmuted_dm_embed(member=member, reason="Timed mute lapsed.", guild=guild):
                    embed.add_field(
                        name="Notice:",
                        value=(
                            f"Unable to message {member.mention} about this action. "
                            "This can be caused by the user not being in the server, "
                            "having DMs disabled, or having the bot blocked."
                        )
                    )

                # Unmutes the user and returns the embed letting the moderator know they were successfully muted.
                await mutes.unmute_member(member=member, reason="Timed mute lapsed.", guild=guild)
                await mutes.archive_mute_channel(user_id=member.id, guild=guild, reason="Mute time elapsed.")
                await channel.send(embed=embed)

            if action["action_type"] == "restrict":
                # Update the database to mark the mod action as resolved.
                db["timed_mod_actions"].update(dict(id=action["id"], is_done=True), ["id"])

                # Get the RestrictCog so that we can access functions from it.
                restricts = self.bot.get_cog("RestrictCog")

                # Attempt to get the member if they still exist in the guild.
                member = guild.get_member(action["user_id"])

                # If the user has left the guild, send a message in #moderation and end the function.
                if not member:
                    # Fetch the user object instead because the user is no longer a member of the server.
                    user = await self.bot.fetch_user(action["user_id"])

                    embed = embeds.make_embed(
                        title=f"Unrestricting member: {user}",
                        description=f"Unrestricted {user.mention} because their restrict time elapsed but they have since left the server.",
                        thumbnail_url="https://i.imgur.com/W7DpUHC.png",
                        color="soft_orange"
                    )

                    return await channel.send(embed=embed)

                # Otherwise, create and send an embed to alert the moderator that the user was unrestricted.
                embed = embeds.make_embed(
                    title=f"Unrestricting member: {member}",
                    thumbnail_url="https://i.imgur.com/W7DpUHC.png",
                    description=f"{member.mention} was unrestricted as their restrict time elapsed.",
                    color="soft_green"
                )

                # Attempt to DM the user to let them know they were unrestricted.
                if not await restricts.send_unrestricted_dm_embed(member=member, reason="Timed restriction lapsed.", guild=guild):
                    embed.add_field(
                        name="Notice:",
                        value=(
                            f"Unable to message {member.mention} about this action. "
                            "This can be caused by the user not being in the server, "
                            "having DMs disabled, or having the bot blocked."
                        )
                    )

                await restricts.unrestrict_member(member=member, reason="Timed restriction lapsed.", guild=guild)
                await channel.send(embed=embed)

        # Close the connection to the database once we're done.
        db.close()


def setup(bot: Bot) -> None:
    """ Load the TimedModActionsTask cog. """
    bot.add_cog(TimedModActionsTask(bot))
    log.info("Cog loaded: timed_mod_actions_task")
