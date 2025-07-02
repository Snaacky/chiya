<p align="center">
<img width="150" height="150" src="https://i.imgur.com/Lkqobis.png">
</p>

<p align="center">
<b>A moderation-heavy general purpose Discord bot.</b>
</p>


## Features
* Avatar grabber
* Bans
* Message purging
* Mutes
* Notes
* Reminders
* Server information
* Tracker status
* Unbans
* Unmutes
* Warns

## Getting started

You will need a Discord bot with [privileged intents](https://discordpy.readthedocs.io/en/stable/intents.html) enabled and the token for that bot before setup. You can create a new Discord bot [here](https://discord.com/developers/). Keep in mind Chiya will need the `bot` and `applications.commands` scopes selected when you generate your OAuth2 URL to function properly.

## Setup
```
$ git clone git@github.com:Snaacky/chiya.git
$ cd chiya
# cp config.example.toml config.toml
$ uv sync
$ uv run python chiya/bot.py
```



