import logging

# Enabling logs
log = logging.getLogger(__name__)

async def record_usage(self, ctx):
    """Recording useage of command"""
    log.info(msg=f"{ctx.author} issued command {ctx.command} @ {ctx.guild} in {ctx.channel}")