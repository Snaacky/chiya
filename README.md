# Chiya - A discord Bot

[![Discord Server](https://img.shields.io/discord/622243127435984927?label=Discord&logo=discord)](https://discord.gg/piracy) 
[![Docker](https://github.com/ranimepiracy/Chiya/workflows/Docker/badge.svg?branch=master)](https://github.com/ranimepiracy/Chiya/actions)

Our private bot for the /r/animepiracy.

---

## Getting started

* Scroll to the FAQ portion of this document if you have questions.
The easiest way is to use [Docker](https://docs.docker.com/engine/reference/run/):

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
    --name=chiya \
    --restart=always \
    -v <location on host where DB is stored>:/app/chiya.db \
    -v <location on host where DB is stored>:/app/config.py \
    docker.pkg.github.com/ranimepiracy/chiya/chiya-bot:latest
```

* Please replace all user variables in the above command defined by <> with the correct values.

### Example

```Shell
docker run -d \
    --name=chiya \
    --restart=always \
    -v /srv/chiya/chiya.db:/app/chiya.db \
    -v /srv/chiya/config.py:/app/config.py \
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
    --name=chiya \
    --restart=always \
    -v /srv/chiya/chiya.db:/app/chiya.db \
    -v /srv/chiya/config.py:/app/config.py \
    chiya-bot
```

# FAQ

## Where do I get a Token to download the docker image?

* Everything you need to learn about creating a Github personal access token can be found [HERE](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token)


## Where can I make a Discord bot token?

* You can find a helpful guide on where and how to make one [HERE](https://www.writebots.com/discord-bot-token/)
* Be sure you set the correct Intents permissions, or your bot might not work correctly.

## Where do I get a Reddit Client ID and Secret?

* You need to make register your bot application on Reddit, you can do that [HERE](https://www.reddit.com/prefs/apps/)
