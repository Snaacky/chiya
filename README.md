<p align="center">
<img width="150" height="150" src="https://i.imgur.com/Lkqobis.png">
</p>

<p align="center">
<b>A moderation-heavy general purpose Discord bot.</b>
</p>

<p align="center">
<a href="https://discord.gg/snackbox"><img src="https://img.shields.io/discord/974468300304171038?label=Discord&logo=discord"></a> <a href="https://github.com/snaacky/chiya/actions"><img src="https://github.com/snaacky/chiya/workflows/Docker/badge.svg?branch=master"></a>
</p>

## Features
* Avatar Grabber
* Bans
* Message purging
* Mutes
* Notes
* Reminders
* Server information
* Tracker status
* Unbans
* Unmutes
* Voting
* Warns

## Getting started

You will need a Discord bot with [privileged intents](https://discordpy.readthedocs.io/en/stable/intents.html) enabled and the token for that bot before setup. You can create a new Discord bot [here](https://discord.com/developers/). Keep in mind Chiya will need the `bot` and `applications.commands` scopes selected when you generate your OAuth2 URL to function properly. If you intend on using the Reddit functionality, you will also need to create a Reddit application [here](https://www.reddit.com/prefs/apps/).

## Setup

Chiya is deployed into a production environment using [Docker](https://docs.docker.com/get-started/) images. As such, the install guide will focus on deployment via Docker. Chiya has been tested on both Windows and Linux bare metal environments and attempts to retain compatibility across both operating systems but this may not always be the case. The install guide assumes that you already have Docker and [docker-compose](https://docs.docker.com/compose/) installed.

#### Steps:
1. Download [`docker-compose.yml`](https://github.com/Snaacky/chiya/blob/master/docker-compose.yml) and fill it out for your deployment. 
2. Create a new directory called `config` in the same directory.  
3. Download [`config.default.yml`](https://github.com/Snaacky/chiya/blob/master/config.default.yml) into `config`, fill it out for your deployment, and rename the file to `config.yml`.
4. Pull the Docker image and start the containers by running `docker-compose up -d`.

## Contributing

Contributors are more than welcome to help make Chiya a better bot. If you are a developer, we encourage you to fork the bot, make changes, and PR your changes upstream. For more information about contributing, [check out our contributing guide](https://github.com/Snaacky/chiya/blob/readme-rework/CONTRIBUTING.md).
