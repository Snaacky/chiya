
<p align="center">
<img width="150" height="150" src="https://i.imgur.com/Lkqobis.png">
</p>

<p align="center">
<b>A moderation-heavy general purpose Discord bot.</b>
</p>

<p align="center">
<a href="https://discord.gg/piracy"><img src="https://img.shields.io/discord/622243127435984927?label=Discord&logo=discord"></a> <a href="https://github.com/ranimepiracy/Chiya/actions"><img src="https://github.com/ranimepiracy/Chiya/workflows/Docker/badge.svg?branch=master"></a>
</p>

## Getting started

Chiya is deployed into a production environment using [Docker](https://docs.docker.com/engine/reference/run/) images. As such, the install guide will focus on deployment via Docker. Chiya has been tested on both Windows and Linux bare metal environments and attempts to retain compatibility across both operating systems but this may not always be the case. The install guide assumes that you already have Docker and [docker-compose](https://docs.docker.com/compose/) installed.

You will also need a Discord bot with [privileged intents](https://discordpy.readthedocs.io/en/stable/intents.html) enabled and the token for that bot before installation. You can create a new Discord bot [here](https://discord.com/developers/). Keep in mind Chiya will need the `bot` and `applications.commands` scopes selected when you generate your OAuth2 URL to function properly. If you intend on using the Reddit functionality, you will also need to create a Reddit application [here](https://www.reddit.com/prefs/apps/).

## Install

**Step 1:** Download the `docker-compose.yml` to your local file system.

**Step 2:** Create a `.env` file in the same folder and fill out the following:

```env
# The bot token for the Discord application
# https://discordapp.com/developers/
BOT_TOKEN=

# The client ID and secret for the Reddit application
# https://www.reddit.com/prefs/apps/
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# The authentication settings for the database
MYSQL_HOST=
MYSQL_DB=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_ROOT_PASSWORD=

# The path on your host file system to config.yml
CONFIG=

# The folder on your host file system for storing database data
DATABASE_FOLDER=

# The folder on your host file system for storing logs
LOGS_FOLDER=
```

**Step 3:** Create a `config.yml` file in the same folder using `config.default.yml` as the base and fill it out. 

**Step 4:** Pull the Docker image and start the containers by running `docker-compose up -d` in the same folder.

## Contributing

Contributors are more than welcome to help make Chiya a better bot. Please follow these steps to get your work merged in:

1. Reach out on Discord and propose your idea beforehand.
2. Clone the repository `git clone` and create a new branch `git checkout -b branch_name` for your work.
3. Add a feature, fix a bug, or refactor some code.
4. Open a Pull Request with a comprehensive list of changes.

## Built on

Chiya relies predominantly on the following projects:

* [Python](https://www.python.org/)
* [MariaDB](https://mariadb.org/)
* [Docker](https://www.docker.com/)
* [discord.py](https://github.com/Rapptz/discord.py)
* [discord-interactions](https://github.com/goverfl0w/discord-interactions)
* [dataset](https://github.com/pudo/dataset)
* [asyncpraw](https://github.com/praw-dev/asyncpraw)
