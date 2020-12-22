import logging
import discord
from discord.ext import commands
from utils import embeds, record

log = logging.getLogger(__name__)


class PlayerInfo(commands.Cog):
	"""PlayerInfo"""

	def __init__(self, bot):
		self.bot = bot

	@commands.command(name='info')
	@commands.is_owner() 
	@commands.before_invoke(record.record_usage)
	async def info(self, ctx, member: discord.Member):
		"""Returns information about a user"""
		
		#log.info(f'{ctx.author} wants to know about: {member.name}.')

		role_list = ' '.join([str(f"•{elm.name}\n") for elm in member.roles])

		embed = embeds.make_embed(
			title=f'{member.display_name}\'s User Info', 
			description="Returning info about selected user", 
			context=ctx, 
			image_url=member.avatar_url
			)
		embed.add_field(name='ID', value=member.id, inline=False)
		embed.add_field(name='Nickname', value=member.nick, inline=False)
		embed.add_field(name='Status', value=member.status, inline=False)
		embed.add_field(name='In Server', value=member.guild, inline=False)
		embed.add_field(name='Joined Server', value=member.joined_at, inline=False)
		embed.add_field(name='Joined Discord', value=member.created_at, inline=False)
		embed.add_field(name='Roles', value=role_list, inline=False)
		# embed.add_field(name='Perms', value=member.guild_permissions, inline=False)
		await ctx.send(embed=embed)
	
	@commands.command(name='profile_picture', aliases=['pfp'])
	@commands.before_invoke(record.record_usage)
	async def pfp(self, ctx, *, member: discord.Member):
		"""Returns the full picture of someones profile picture."""
		
		log.info(f'{ctx.author} wanted to see {member.name}\'s beautiful face.')
		
		embed = embeds.make_embed(
			title=f"{member.display_name}'s profile picture",
			context=ctx)
		embed.set_image(url=member.avatar_url_as(size=4096))
		await ctx.send(embed=embed)
	
	@commands.command(name='perms', aliases=['perms_for', 'permissions'])
	@commands.guild_only()
	@commands.before_invoke(record.record_usage)
	async def check_permissions(self, ctx, *, member: discord.Member = None):
		"""A simple command which checks a members Guild Permissions.
		If member is not provided, the author will be checked."""
		
		if not member:
			member = ctx.author
		
		# Here we check if the value of each permission is True.
		perms = '\n'.join(perm for perm, value in member.guild_permissions if value)
		
		# And to make it look nice, we wrap it in an Embed.
		embed = discord.Embed(
			title='Permissions for:', 
			description=ctx.guild.name, 
			colour=member.colour,
			context=ctx)
		
		# \uFEFF is a Zero-Width Space, which basically allows us to have an empty field name.
		embed.add_field(name='\uFEFF', value=perms)
		
		await ctx.send(embed=embed)


def setup(bot):
	bot.add_cog(PlayerInfo(bot))
	log.info("Cog loaded: PlayerInfo")