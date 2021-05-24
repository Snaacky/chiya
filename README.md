# Chiya

[![Discord Server](https://img.shields.io/discord/622243127435984927?label=Discord&logo=discord)](https://discord.gg/piracy) 
[![Docker](https://github.com/ranimepiracy/Chiya/workflows/Docker/badge.svg?branch=master)](https://github.com/ranimepiracy/Chiya/actions)

---

## Getting started

The easiest way to get started running Chiya is by using [Docker](https://docs.docker.com/engine/reference/run/) however the bot should run in both virtualized and bare metal environments across Windows and \*nix based platforms. Our setup guide will focus on setting up the bot with Docker as that is what we use in our productione environment. 

**Step 1:**
As the Docker image is currently hosted on a private Github repo, you will need to login into the Github container registry first.

```Shell
docker login https://docker.pkg.github.com -u USERNAME -p TOKEN
```

* If security is a concern, pass the token as pipe instead of saving your token in your `.bash_history`.

```Shell
cat ~/TOKEN.txt | docker login https://docker.pkg.github.com -u USERNAME --password-stdin
```

**Step 2:**
Run the following command to download and run the container:

```Shell
    docker run -d \
    --name=chiya \
    --restart unless-stopped \
    -v <location on host where DB is stored>:/app/chiya.db \
    -v <location on host where DB is stored>:/app/config.py \
    -v <location to store logs>:/app/logs/ \
    docker.pkg.github.com/ranimepiracy/chiya/chiya-bot:latest
```

* Make sure to replace the variables in the above command defined by `<>` with the correct values for your local environment.

### Example

```Shell
docker run -d \
    --name=chiya \
    --restart unless-stopped \
    -v /srv/chiya/chiya.db:/app/chiya.db \
    -v /srv/chiya/config.py:/app/config.py \
    -v /srv/chiya/logs/:/app/logs/ \
    docker.pkg.github.com/ranimepiracy/chiya/chiya-bot:latest
```

The bot should now be running.

---

## Building from source code

**Step 1:**
Download the source files to your local machine and open up a terminal at that location.

**Step 2:**
Build the [Docker image](https://docs.docker.com/engine/reference/commandline/build/) with the following command:

```Shell
docker build . -t chiya-bot
```

**Step 3:**
Run the container with the following command:

```Shell
docker run -d \
    --name=chiya \
    --restart unless-stopped \
    -v /srv/chiya/chiya.db:/app/chiya.db \
    -v /srv/chiya/config.py:/app/config.py \
    -v /srv/chiya/logs/:/app/logs/ \
    chiya-bot
```

# FAQ

## Where do I get a token to download the Docker image?

* Everything you need to learn about creating a Github Personal Access Token can be found [here](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token).


## Where can I create a Discord bot token?

* You can find a helpful guide on where and how to make one [here](https://www.writebots.com/discord-bot-token/).
* Be sure you set the correct Intents permissions, or your bot might not work correctly.

## Where do I get a Reddit client ID and secret?

* You need to make register your bot application on Reddit, you can do that [here](https://www.reddit.com/prefs/apps/).
