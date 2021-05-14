
import logging
from datetime import datetime, timezone

import dataset
import discord
from discord.ext import tasks
from discord.ext.commands import Bot, Cog

from utils import database, embeds
import config

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

        time_now = datetime.now(tz=timezone.utc)
        
        async def unmute(member: discord.Member, channel: discord.TextChannel):
            """ Unmutes member and logs the action. """
            guild = self.bot.get_guild(config.guild_id)
            embed = embeds.make_embed(title=f"Unmuting member: {member}",
                image_url=config.user_unmute, color="soft_green")
            embed.description=f"{member.mention} was unmuted as their mute time lapsed."

            try: # Incase user has DM's Blocked.
                dm_channel = await member.create_dm()
                mute_embed = embeds.make_embed(author=False, color=0x8a3ac5)
                mute_embed.title = f"Yay, you've been unmuted!"
                mute_embed.description = "Review our server rules to avoid being actioned again in the future."
                mute_embed.add_field(name="Server:", value=guild, inline=True)
                mute_embed.add_field(name="Reason:", value="Timed mute lapsed.", inline=False)
                mute_embed.set_image(url="https://i.imgur.com/U5Fvr2Y.gif")
                await dm_channel.send(embed=mute_embed)
            except:
                embed.add_field(name="Notice:", value="Unable to message member about this action.")
            
            role = discord.utils.get(guild.roles, name="Muted")
            await member.remove_roles(role, reason="Timed mute lapsed.")

            if channel:
                await channel.send(embed=embed)
        
        async def unban(user: discord.User, channel: discord.TextChannel):
            """ Unbans member and logs the action. """
            guild = self.bot.get_guild(config.guild_id)
            
            embed = embeds.make_embed(ctx=None, title=f"Unbanning user: {user}", 
            image_url=config.user_unban, color="soft_green")
            embed.description=f"{user.mention} was unbanned as their ban time lapsed."

            await guild.unban(user=user, reason="Ban time lapsed.")
            
            await channel.send(embed=embed)

        result = None
        guild = self.bot.get_guild(config.guild_id)

        with dataset.connect(database.get_db()) as db:
            result = db["timed_mod_actions"].find(
                is_done = False,
                end_time = {
                    'lt': datetime.now(tz=timezone.utc).timestamp()
                }
            )

        for action in result:
            channel = guild.get_channel(action['channel_id'])
            user_id = action['user_id']

            if action['action_type'] == 'mute':
                # unmuting requires Member
                member = None
                try:
                    member = await guild.fetch_member(user_id)
                except:
                    pass

                if member:
                    await unmute(member, channel)

                with dataset.connect(database.get_db()) as db:
                    db['mod_logs'].insert(dict(
                        user_id=member.id, 
                        mod_id=action['mod_id'], 
                        timestamp=time_now.timestamp(), 
                        reason="Timed mute lapsed.", 
                        type="unmute"
                        ))

                    db['timed_mod_actions'].update(dict(id=action['id'], is_done=True), ['id'])    
            
            if action['action_type'] == 'ban':
                member = await self.bot.fetch_user(user_id)

                await unban(member, channel)
                with dataset.connect(database.get_db()) as db:
                    db['mod_logs'].insert(dict(
                        user_id=member.id, 
                        mod_id=action['mod_id'], 
                        timestamp=time_now.timestamp(), 
                        reason="Timed ban lapsed.", 
                        type="unban"
                        ))

                    db['timed_mod_actions'].update(dict(id=action['id'], is_done=True), ['id'])

def setup(bot: Bot) -> None:
    """ Load the TimedModActionsTask cog. """
    bot.add_cog(TimedModActionsTask(bot))
    log.info("Cog loaded: timed_mod_actions_task")