import logging

import discord
from discord.ext import commands

from chiya import config
from chiya.utils import embeds


log = logging.getLogger(__name__)


class AutoresponderListeners(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Scan incoming messages for autoresponder invokes (case-insensitive)
        and replies with the appopriate embed. Currently only when invoked
        by a staff member.
        """
        if message.author.bot:
            return

        staff = [x for x in message.author.roles
                 if x.id == config["roles"]["staff"]
                 or x.id == config["roles"]["trial"]]
        if not staff:
            return

        rules_message = "https://discord.com/channels/974468300304171038/974483470548099104/984329857007747094"
        match message.clean_content.lower():
            case "rule1":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 1: Do not share content that violates anyone's intellectual property or other rights",
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
                    title="Rule 2: Do not spread any form of hate speech. Irony or jokes are not an excuse",
                    description=(
                        "Any form of prejudice, including but not limited to race, "
                        "religion, gender, sexual identity, or ethnic background, will not be tolerated."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/Q9HVxLK.png",
                    title_url=rules_message
                ))
            case "rule3":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 3: Do not attack others, troll, or instigate drama",
                    description=(
                        "Attacking, belittling, or instigating drama with others will result in your removal "
                        "from the community."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/7OLIuky.png",
                    title_url=rules_message
                ))
            case "rule4":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 4: Do not spam (text, images, links, Tenor gifs) or disrupt the flow of chat",
                    description=(
                        "Avoid spamming, derailing conversations, trolling, posting in the incorrect channel, "
                        "or disregarding channel rules. We expect you to make a basic attempt to fit in and "
                        "not cause problems."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/37s6rUa.png",
                    title_url=rules_message
                ))
            case "rule5":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 5: Do not ghost ping, spam ping, ping VIPs for support, or abuse pings in any way",
                    description=(
                        "Attempting to mass ping, spam ping, ghost ping, or harassing users with pings is not "
                        "allowed. VIPs should not be pinged for help with their service. <@&974483014967001119> "
                        "should only be pinged when the situation calls for their immediate attention."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/4a5K4c6.png",
                    title_url=rules_message
                ))
            case "rule6":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 6: Do not ask for, giveaway, or attempt to buy/sell/trade tracker invites",
                    description=(
                        "Invites are intended for personal acquaintances. "
                        "Publicly offering, requesting, or giving away invites to private trackers, "
                        "DDL communities, or Usenet indexers is not allowed."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/W17MO9d.png",
                    title_url=rules_message
                ))
            case "rule7":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 7: Do not advertise other Discord servers or services",
                    description=(
                        "We are not a billboard for you to advertise your Discord server, social media "
                        "channels, referral links, personal projects, or services. "
                        "Unsolicited spam via DMs will result in an immediate ban."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/7cJCnh0.png",
                    title_url=rules_message
                ))
            case "rule8":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 8: Do not use offensive or edgy text or imagery on your profile",
                    description=(
                        "Users with excessively offensive usernames, nicknames, avatars, server "
                        "profiles, or statuses may be asked to change the offending content or may be "
                        "preemptively banned in more severe cases."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/xbvjFRq.png",
                    title_url=rules_message
                ))
            case "rule9":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 9: Do not attempt to evade automod or mod actions",
                    description=(
                        "Abusing the rules, such as our automod system, will not be tolerated. Subsequently, "
                        "trying to find loopholes in the rules to evade mod action is not allowed and "
                        "will result in a permanent ban."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/Nfcrq1N.png",
                    title_url=rules_message
                ))
            case "rule10":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 10: Spoilers must be marked in spoiler tags and be clearly labeled",
                    description=(
                        "Be considerate and use spoiler tags when discussing plot elements. "
                        "Specify which title, series, or episode your spoiler is referencing outside the spoiler tag "
                        "so that people don't blindly click a spoiler."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/wNZxV36.png",
                    title_url=rules_message
                ))
            case "rule11":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 11: References to banned users or banned communities are not allowed",
                    description=(
                        "Do not discuss or reference any banned users or banned communities as "
                        "they have been banned for a reason already discussed by staff with no"
                        "need for further discussions."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/2ZxCttO.png",
                    title_url=rules_message
                ))
            case "rule12":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 12: All conversations must be in English",
                    description=(
                        "No language other than English is permitted. We appreciate other languages "
                        "and cultures, but we can only moderate the content we understand."
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/EQvl6Lm.png",
                    title_url=rules_message
                ))
            case "rule13":
                await message.reply(embed=embeds.make_embed(
                    title="Rule 13: Do not discuss your sexual endeavors or relationships",
                    description=(
                        "Discussion of NSFW topics like sex and fetishes are not allowed "
                        "outside of NSFW channels. "
                    ),
                    color=0x7d98e9,
                    thumbnail_url="https://i.imgur.com/GgL8pPz.png",
                    title_url=rules_message
                ))


def setup(bot) -> None:
    bot.add_cog(AutoresponderListeners(bot))
    log.info("Listeners Loaded: autoresponder")
