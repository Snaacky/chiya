![Docker](https://github.com/ranimepiracy/Chiya/workflows/Docker/badge.svg?branch=master)
# Chiya
Our private bot for the /r/animepiracy [Discord server](https://discord.gg/piracy).

# Getting started
The easiest way is to use [docker](https://docs.docker.com/engine/reference/run/) via:
```
docker run -d docker.pkg.github.com/ranimepiracy/chiya/chiya-bot
```
As the container images are currently hosted on privat github, you will need to login into the github container registry first with your personal access token **BEFORE** you run the previous command
```
docker login https://docker.pkg.github.com -u USERNAME -p TOKEN
```
ideally you pass the token as pipe instead of saving your token in your bash-history, resulting in potential security risks with
```
cat ~/TOKEN.txt | docker login https://docker.pkg.github.com -u USERNAME --password-stdin
```

## Building from source
To build the [docker image](https://docs.docker.com/engine/reference/commandline/build/) you will need to run:
```
docker build . -t chiya-bot
```
Afterwards you will just need to run
```
docker run -d chiya-bot
```
