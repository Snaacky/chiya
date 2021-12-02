import logging

from discord import Message
from discord.ext import commands

from utils import embeds
from utils.config import config


log = logging.getLogger(__name__)


class AutoResponders(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return

        staff = [x for x in message.author.roles
                 if x.id == config["roles"]["staff"]
                 or x.id == config["roles"]["trial_mod"]]
        if not staff:
            return

        rules_message = "https://ptb.discord.com/channels/622243127435984927/623100638812962816/904426149491400715"
        match message.clean_content.lower():
            case "rule1":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 1: Do not share copyright infringing files or links",
                    description=(
                        "Sharing illegal streaming sites, downloads, torrents, magnet links, trackers, "
                        "NZBs, or any other form of warez puts our community at risk of being shut down. "
                        "We are a discussion community, not a file-sharing hub."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/X0upMFa.png",
                    title_url=rules_message
                ))
            case "rule2":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 2: Treat others the way you want to be treated",
                    description=(
                        "Attacking, belittling, or instigating drama with others will result in your removal "
                        "from the community. Any form of prejudice, including but not limited to race, "
                        "religion, gender, sexual identity, or ethnic background, will not be tolerated."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/Q9HVxLK.png",
                    title_url=rules_message
                ))
            case "rule3":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 3: Do not disrupt chat",
                    description=(
                        "Avoid spamming, derailing conversations, trolling, posting in the incorrect channel, "
                        "or disregarding channel rules. We expect you to make a basic attempt to fit in and "
                        "not cause problems."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/7OLIuky.png",
                    title_url=rules_message
                ))
            case "rule4":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 4: Do not abuse pings",
                    description=(
                        "Attempting to mass ping, spam ping, ghost ping, or harassing users with pings is not "
                        "allowed. VIPs should not be pinged for help with their service. <@&763031634379276308> "
                        "should only be pinged when the situation calls for their immediate attention."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/37s6rUa.png",
                    title_url=rules_message
                ))
            case "rule5":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 5: Do not attempt to evade mod actions",
                    description=(
                        "Abusing the rules, such as our automod system, will not be tolerated. Subsequently, "
                        "trying to find loopholes in the rules to evade mod action is not allowed and "
                        "will result in a permanent ban."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/4a5K4c6.png",
                    title_url=rules_message
                ))
            case "rule6":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 6: Do not post unmarked spoilers",
                    description=(
                        "Be considerate and use spoiler tags when discussing plot elements. "
                        "Specify which title, series, or episode your spoiler is referencing outside the spoiler tag "
                        "so that people don't blindly click a spoiler."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/W17MO9d.png",
                    title_url=rules_message
                ))
            case "rule7":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 7: All conversation must be in English",
                    description=(
                        "No language other than English is permitted. We appreciate other languages "
                        "and cultures, but we can only moderate the content we understand."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/7cJCnh0.png",
                    title_url=rules_message
                ))
            case "rule8":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 8: Do not post self-promotional content",
                    description=(
                        "We are not a billboard for you to advertise your Discord server, social media "
                        "channels, referral links, personal projects, or services. "
                        "Unsolicited spam via DMs will result in an immediate ban."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/xbvjFRq.png",
                    title_url=rules_message
                ))
            case "rule9":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 9: One account per person per lifetime",
                    description=(
                        "Anyone found sharing or using alternate accounts will be banned. "
                        "Contact staff if you feel you deserve an exception."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/Nfcrq1N.png",
                    title_url=rules_message
                ))
            case "rule10":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 10: Do not give away, trade, or misuse invites",
                    description=(
                        "Invites are intended for personal acquaintances. "
                        "Publicly offering, requesting, or giving away invites to private trackers, "
                        "DDL communities, or Usenet indexers is not allowed."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/wNZxV36.png",
                    title_url=rules_message
                ))
            case "rule11":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 11: Do not post NSFL content",
                    description=(
                        "NSFL content is described as \"content which is so nauseating or disturbing "
                        "that it might be emotionally scarring to view.\" Content marked NSFL may contain "
                        "fetish pornography, gore, or lethal violence."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/2ZxCttO.png",
                    title_url=rules_message
                ))
            case "rule12":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 12: Egregious profiles are not allowed",
                    description=(
                        "Users with excessively offensive usernames, nicknames, avatars, server "
                        "profiles, or statuses may be asked to change the offending content or may be "
                        "preemptively banned in more severe cases."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/EQvl6Lm.png",
                    title_url=rules_message
                ))


def setup(bot) -> None:
    bot.add_cog(AutoResponders(bot))
    log.info("Listener Loaded: autoresponders")
