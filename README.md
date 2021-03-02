# Chiya - A discord Bot

[![Discord Server](https://img.shields.io/discord/622243127435984927?label=Discord&logo=discord)](https://discord.gg/piracy) ![Docker](https://github.com/ranimepiracy/Chiya/workflows/Docker/badge.svg?branch=master)

Our private bot for the /r/animepiracy.

---

## Getting started

* Scroll to the FAQ portion of this document if you have questions.
The easiest way is to use [docker](https://docs.docker.com/engine/reference/run/):

**Step 1:**
As the docker image is currently hosted on a private Github repo, you will need to login into the Github container registry first.

```Shell
docker login https://docker.pkg.github.com -u USERNAME -p TOKEN
```

* If security is a concern, pass the token as pipe instead of saving your token in your bash-history.

```Shell
cat ~/TOKEN.txt | docker login https://docker.pkg.github.com -u USERNAME --password-stdin
```

**Step 2:**
Run this script to auto-download and run the container.

```Shell
docker run -d \
    --net="bridge" \
    --name=chiya-bot \
    -v <location you wish to keep database file>:/app/DATABASE.db \
    -v <location you wish to edit config file>:/app/config.yml \
    -e BOT_PREFIX=<symbol(s) that you want to begin bot commands with> \
    -e BOT_TOKEN=<Discord bot token> \
    -e LOG_LEVEL=INFO \
    -e REDDIT_SUBREDDIT=<subreddit you wish to monitor after /r/> \
    -e REDDIT_CLIENT_ID=<reddit bot client id> \
    -e REDDIT_SECRET=<reddit bot secret token> \
    -e REDDIT_USER_AGENT=<reddit bot username> \
    docker.pkg.github.com/ranimepiracy/chiya/chiya-bot:latest
```

* Please replace all user variables in the above command defined by <> with the correct values.

### Example

```Shell
docker run -d \
    --net="bridge" \
    --name=chiya-bot \
    -v /apps/docker/chiya-bot:/app/DATABASE.db \
    -v /apps/docker/chiya-bot:/app/config.yml \
    -e BOT_PREFIX=$ \
    -e BOT_TOKEN=ODA4ODUxOTg1NzMzMjU1MTk5.YCMkHQ.LuFw9zNYYYrAh2nAZwXZcWSy60A \
    -e LOG_LEVEL=INFO \
    -e REDDIT_SUBREDDIT=animepiracy \
    -e REDDIT_CLIENT_ID=cNleNeyDrkHifh \
    -e REDDIT_SECRET=BkkSYrd7fPJpx7k6yWlKTd6oNnobiS \
    -e REDDIT_USER_AGENT=chiyadiscordbot \
    docker.pkg.github.com/ranimepiracy/chiya/chiya-bot:latest
```

Bot should now be running.

---

## Building from source code

**Step 1:**
Download source files to your computer and open up a command-line-interface at that location.

**Step 2:**
Build the [Docker image](https://docs.docker.com/engine/reference/commandline/build/) with the following command:

```Shell
docker build . -t chiya-bot
```

**Step 3:**
Run the container with this command.

```Shell
docker run -d \
    --net="bridge" \
    --name=<container name> \
    -v /apps/docker/chiya-bot:/app/DATABASE.db \
    -v /apps/docker/chiya-bot:/app/config.yml \
    -e BOT_PREFIX=PASTE_BOT_PREFIX_HERE \
    -e BOT_TOKEN=PASTE_BOT_TOKEN_HERE \
    -e LOG_LEVEL=INFO \
    -e REDDIT_SUBREDDIT=SUBREDDIT_NAME \
    -e REDDIT_CLIENT_ID=REDDIT_BOT_CLIENT_ID \
    -e REDDIT_SECRET=REDDIT_BOT_SECRET \
    -e REDDIT_USER_AGENT=REDDIT_BOT_USER_AGENT \
    chiya-bot
```

# FAQ

## Where do I get a Token to download the docker image?

* Everything you need to learn about creating a Github personal access token can be found [HERE](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token)

## Why is the docker command so long?

* The environmental variables do not have to be in the command but it is simple for them to be located there. If you do not wish for them to be located there because of security or other reasons, you can use the `config.yml` file for that usage instead. You simply follow the syntax of the [`config-default.yml`](https://github.com/ranimepiracy/Chiya/blob/master/config-default.yml) and **ONLY** type what you want to change or else you may break future changes.
* Here is an example of what the two files look like compared to each other. Be sure you remove the `!ENV` Infix.
![IMAGE](https://i.imgur.com/bJsGCyY.png)

## Where can I make a Discord bot token?

* You can find a helpful guide on where and how to make one [HERE](https://www.writebots.com/discord-bot-token/)
* Be sure you set the correct Intents permissions, or your bot might not work correctly.

## Where do I get a Reddit Client ID and Secret?

* You need to make register your bot application on Reddit, you can do that [HERE](https://www.reddit.com/prefs/apps/)
